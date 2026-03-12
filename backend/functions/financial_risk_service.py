import sys, os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_GRAPH_URI, VALIDATION_REPORT_URI
from functions.invoice_service import _sparql, _val

SH      = "http://www.w3.org/ns/shacl#"
EDIFACT = "https://purl.org/edifact/ontology#"
P2P_DOC = "https://purl.org/p2p-o/document#"
P2P_INV = "https://purl.org/p2p-o/invoice#"
P2P_ORG = "https://purl.org/p2p-o/organization#"
SCHEMA  = "http://schema.org/"


def _invoice_amounts():
    """Return {invoice_uri: amount_float} for all invoices that have an amount."""
    rows = _sparql(f"""
        SELECT ?inv ?amt1 ?amt2
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            ?inv a <{P2P_DOC}E-Invoice> .
            OPTIONAL {{
                ?inv <{EDIFACT}hasInvoiceDetails> ?d .
                OPTIONAL {{ ?d <{EDIFACT}hasInvoiceAmount>       ?amt1 }}
                OPTIONAL {{ ?d <{EDIFACT}hasTotalAmountMessage>  ?amt2 }}
            }}
        }}
    """)
    result = {}
    for b in rows:
        uri = b["inv"]["value"]
        raw = (b.get("amt1") or b.get("amt2") or {}).get("value")
        result[uri] = float(raw) if raw else 0.0
    return result


def _violation_counts():
    """Return {invoice_uri: violation_count} aggregated across all related nodes."""
    # Step 1 – count per focus-node
    fn_rows = _sparql(f"""
        SELECT ?fn (COUNT(?v) AS ?c)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{ ?v a <{SH}ValidationResult> ; <{SH}focusNode> ?fn . }}
        GROUP BY ?fn
    """)
    fn_counts = {b["fn"]["value"]: int(b["c"]["value"]) for b in fn_rows}
    if not fn_counts:
        return {}

    # Step 2 – map focus-nodes → invoices (chunked)
    inv_counts = {}
    chunk_size = 80
    fns = list(fn_counts.keys())
    for i in range(0, len(fns), chunk_size):
        chunk = fns[i:i+chunk_size]
        vals  = " ".join(f"<{u}>" for u in chunk)
        rows  = _sparql(f"""
            SELECT DISTINCT ?inv ?fn
            FROM <{DATA_GRAPH_URI}>
            WHERE {{
                VALUES ?fn {{ {vals} }}
                {{
                    ?fn a <{P2P_DOC}E-Invoice> . BIND(?fn AS ?inv)
                }} UNION {{
                    ?inv a <{P2P_DOC}E-Invoice> . ?inv ?p ?fn .
                }} UNION {{
                    ?inv a <{P2P_DOC}E-Invoice> . ?inv ?p1 ?mid . ?mid ?p2 ?fn .
                }}
            }}
        """)
        for b in rows:
            inv = b["inv"]["value"]
            fn  = b["fn"]["value"]
            inv_counts[inv] = inv_counts.get(inv, 0) + fn_counts.get(fn, 0)
    return inv_counts


def _supplier_names():
    """Return {invoice_uri: supplier_name}."""
    rows = _sparql(f"""
        SELECT ?inv ?n1 ?n2
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            ?inv a <{P2P_DOC}E-Invoice> .
            OPTIONAL {{ ?inv <{P2P_INV}hasSupplier> ?s . ?s <{P2P_ORG}formalName> ?n1 }}
            OPTIONAL {{ ?inv <{P2P_INV}hasPayee>    ?p . ?p <{P2P_ORG}formalName> ?n2 }}
        }}
    """)
    result = {}
    for b in rows:
        uri = b["inv"]["value"]
        name = (b.get("n1") or b.get("n2") or {}).get("value")
        if name:
            result[uri] = name
    return result


# ── public functions ─────────────────────────────────────────────────────────

def get_financial_risk_summary():
    """Top-level KPIs: total/blocked/at-risk value, counts, aging buckets."""
    amounts      = _invoice_amounts()
    viol_counts  = _violation_counts()
    supplier_map = _supplier_names()

    total_value    = 0.0
    blocked_value  = 0.0
    at_risk_value  = 0.0
    blocked_count  = 0
    at_risk_count  = 0
    compliant_count = 0

    # Aging buckets by invoice document date (days since date field or absent)
    # We classify by violation severity proxy: ≥3 violations = blocked, 1-2 = at-risk
    for uri, amount in amounts.items():
        total_value += amount
        vc = viol_counts.get(uri, 0)
        if vc >= 3:
            blocked_value += amount
            blocked_count += 1
        elif vc > 0:
            at_risk_value += amount
            at_risk_count += 1
        else:
            compliant_count += 1

    return {
        "totalValue":      round(total_value, 2),
        "blockedValue":    round(blocked_value, 2),
        "atRiskValue":     round(at_risk_value, 2),
        "blockedCount":    blocked_count,
        "atRiskCount":     at_risk_count,
        "compliantCount":  compliant_count,
        "totalCount":      len(amounts),
    }


def get_exposure_by_supplier():
    """Blocked + at-risk value and invoice counts grouped by supplier name."""
    amounts      = _invoice_amounts()
    viol_counts  = _violation_counts()
    supplier_map = _supplier_names()

    data = {}   # supplier_name → { blockedValue, atRiskValue, blockedCount, atRiskCount }
    for uri, amount in amounts.items():
        name = supplier_map.get(uri, "Unknown")
        vc   = viol_counts.get(uri, 0)
        if vc == 0:
            continue
        if name not in data:
            data[name] = {"supplier": name, "blockedValue": 0.0, "atRiskValue": 0.0,
                          "blockedCount": 0, "atRiskCount": 0}
        if vc >= 3:
            data[name]["blockedValue"]  += amount
            data[name]["blockedCount"]  += 1
        else:
            data[name]["atRiskValue"]   += amount
            data[name]["atRiskCount"]   += 1

    result = list(data.values())
    for row in result:
        row["blockedValue"] = round(row["blockedValue"], 2)
        row["atRiskValue"]  = round(row["atRiskValue"],  2)
        row["totalRisk"]    = round(row["blockedValue"] + row["atRiskValue"], 2)

    result.sort(key=lambda r: r["totalRisk"], reverse=True)
    return result


def get_exposure_by_doc_type():
    """Blocked + at-risk value grouped by document type."""
    # Fetch document types
    type_rows = _sparql(f"""
        SELECT ?inv ?docType
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            ?inv a <{P2P_DOC}E-Invoice> .
            OPTIONAL {{ ?inv <{EDIFACT}hasInvoiceDetails> ?d . ?d <{EDIFACT}hasDocumentType> ?docType }}
        }}
    """)
    type_map = {b["inv"]["value"]: _val(b, "docType") or "Unknown" for b in type_rows}

    amounts     = _invoice_amounts()
    viol_counts = _violation_counts()

    data = {}
    for uri, amount in amounts.items():
        dt = type_map.get(uri, "Unknown")
        vc = viol_counts.get(uri, 0)
        if vc == 0:
            continue
        if dt not in data:
            data[dt] = {"docType": dt, "blockedValue": 0.0, "atRiskValue": 0.0,
                        "blockedCount": 0, "atRiskCount": 0}
        if vc >= 3:
            data[dt]["blockedValue"] += amount
            data[dt]["blockedCount"] += 1
        else:
            data[dt]["atRiskValue"]  += amount
            data[dt]["atRiskCount"]  += 1

    result = list(data.values())
    for row in result:
        row["blockedValue"] = round(row["blockedValue"], 2)
        row["atRiskValue"]  = round(row["atRiskValue"],  2)
    result.sort(key=lambda r: r["blockedValue"] + r["atRiskValue"], reverse=True)
    return result


def get_high_value_risk_invoices(top_n=20):
    """List of at-risk/blocked invoices sorted by amount descending."""
    amounts      = _invoice_amounts()
    viol_counts  = _violation_counts()
    supplier_map = _supplier_names()

    # Fetch doc numbers in one query
    num_rows = _sparql(f"""
        SELECT ?inv ?docNum ?currency
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            ?inv a <{P2P_DOC}E-Invoice> .
            OPTIONAL {{ ?inv <{EDIFACT}hasInvoiceDetails> ?d .
                        ?d <{EDIFACT}hasDocumentNumber> ?docNum .
                        OPTIONAL {{ ?d <{SCHEMA}currency> ?currency }} }}
        }}
    """)
    meta = {b["inv"]["value"]: {
        "docNumber": _val(b, "docNum"),
        "currency":  _val(b, "currency"),
    } for b in num_rows}

    rows = []
    for uri, amount in amounts.items():
        vc = viol_counts.get(uri, 0)
        if vc == 0:
            continue
        rows.append({
            "uri":            uri,
            "id":             uri.split("/")[-1],
            "documentNumber": (meta.get(uri) or {}).get("docNumber"),
            "currency":       (meta.get(uri) or {}).get("currency"),
            "amount":         round(amount, 2),
            "violationCount": vc,
            "status":         "Blocked" if vc >= 3 else "At Risk",
            "supplier":       supplier_map.get(uri, "Unknown"),
        })

    rows.sort(key=lambda r: r["amount"], reverse=True)
    return rows[:top_n]


def get_aging_buckets():
    """Count and value of at-risk/blocked invoices bucketed by violation-count proxy.

    Since the snapshot has no timestamps, we bucket by violation severity:
    0-1 viol = Low, 2-4 = Medium, 5-9 = High, 10+ = Critical
    """
    amounts     = _invoice_amounts()
    viol_counts = _violation_counts()

    buckets = {
        "Low (1-2 violations)":      {"count": 0, "value": 0.0},
        "Medium (3-4 violations)":   {"count": 0, "value": 0.0},
        "High (5-9 violations)":     {"count": 0, "value": 0.0},
        "Critical (10+ violations)": {"count": 0, "value": 0.0},
    }

    for uri, amount in amounts.items():
        vc = viol_counts.get(uri, 0)
        if vc == 0:
            continue
        if vc <= 2:
            key = "Low (1-2 violations)"
        elif vc <= 4:
            key = "Medium (3-4 violations)"
        elif vc <= 9:
            key = "High (5-9 violations)"
        else:
            key = "Critical (10+ violations)"
        buckets[key]["count"] += 1
        buckets[key]["value"] += amount

    result = []
    for label, d in buckets.items():
        result.append({"bucket": label, "count": d["count"], "value": round(d["value"], 2)})
    return result
