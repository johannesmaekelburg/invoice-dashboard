import sys, os, re
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import DATA_GRAPH_URI, VALIDATION_REPORT_URI
from functions.invoice_service import _sparql, _val

SH      = "http://www.w3.org/ns/shacl#"
EDIFACT = "https://purl.org/edifact/ontology#"
P2P_DOC = "https://purl.org/p2p-o/document#"
P2P_INV = "https://purl.org/p2p-o/invoice#"
P2P_ORG = "https://purl.org/p2p-o/organization#"


def _short(uri):
    """Return the local name of a URI."""
    if not uri:
        return "Unknown"
    return re.split(r"[#/]", uri)[-1]


def _humanize(path_or_label):
    """Turn a camelCase / underscore name into a readable label."""
    if not path_or_label:
        return "Unknown"
    label = _short(path_or_label)
    # insert space before uppercase letters
    label = re.sub(r"(?<=[a-z])([A-Z])", r" \1", label)
    label = label.replace("_", " ").strip()
    return label


def _supplier_names():
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
        uri  = b["inv"]["value"]
        name = (b.get("n1") or b.get("n2") or {}).get("value")
        if name:
            result[uri] = name
    return result


def _buyer_names():
    rows = _sparql(f"""
        SELECT ?inv ?n1 ?n2
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            ?inv a <{P2P_DOC}E-Invoice> .
            OPTIONAL {{ ?inv <{P2P_INV}hasBuyer>          ?b . ?b <{P2P_ORG}formalName> ?n1 }}
            OPTIONAL {{ ?inv <{EDIFACT}hasInvoicee>        ?i . ?i <{P2P_ORG}formalName> ?n2 }}
        }}
    """)
    result = {}
    for b in rows:
        uri  = b["inv"]["value"]
        name = (b.get("n1") or b.get("n2") or {}).get("value")
        if name:
            result[uri] = name
    return result


def _all_violations():
    """
    Return a list of dicts with keys:
      invoice_uri, focus_node, result_path, shape_name, severity, message
    """
    # Step 1: all violations with path/shape/severity
    viol_rows = _sparql(f"""
        SELECT ?v ?fn ?path ?shape ?sev ?msg
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v a <{SH}ValidationResult> ;
               <{SH}focusNode> ?fn .
            OPTIONAL {{ ?v <{SH}resultPath>     ?path  }}
            OPTIONAL {{ ?v <{SH}sourceShape>    ?shape }}
            OPTIONAL {{ ?v <{SH}resultSeverity> ?sev   }}
            OPTIONAL {{ ?v <{SH}resultMessage>  ?msg   }}
        }}
    """)

    fn_to_violation = []  # list of (focus_node_uri, path, shape, sev, msg)
    fn_set = set()
    for b in viol_rows:
        fn  = b["fn"]["value"]
        fn_set.add(fn)
        fn_to_violation.append({
            "fn":    fn,
            "path":  _val(b, "path"),
            "shape": _val(b, "shape"),
            "sev":   _val(b, "sev"),
            "msg":   _val(b, "msg"),
        })

    if not fn_set:
        return []

    # Step 2: map focus-nodes → invoice URIs
    fn_to_inv = {}
    chunk_size = 80
    fn_list = list(fn_set)
    for i in range(0, len(fn_list), chunk_size):
        chunk = fn_list[i:i+chunk_size]
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
            fn_to_inv[b["fn"]["value"]] = b["inv"]["value"]

    enriched = []
    for v in fn_to_violation:
        inv = fn_to_inv.get(v["fn"])
        if inv:
            enriched.append({**v, "invoice_uri": inv})
    return enriched


# ── public functions ─────────────────────────────────────────────────────────

def get_issue_summary():
    """KPIs: distinct issue types, most frequent, most impactful by invoice count."""
    violations = _all_violations()

    category_counts = {}
    for v in violations:
        cat = _humanize(v["path"] or v["shape"])
        category_counts[cat] = category_counts.get(cat, 0) + 1

    top = sorted(category_counts.items(), key=lambda x: x[1], reverse=True)
    return {
        "totalViolations":   len(violations),
        "distinctCategories": len(category_counts),
        "topCategory":        top[0][0] if top else None,
        "topCategoryCount":   top[0][1] if top else 0,
    }


def get_top_issue_categories(top_n=20):
    """
    Ranked list of issue categories with:
      - violation count
      - affected invoice count
      - affected supplier count
    """
    violations   = _all_violations()
    supplier_map = _supplier_names()

    # Aggregate per category
    data = {}  # cat → {count, inv_set, supplier_set}
    for v in violations:
        cat = _humanize(v["path"] or v["shape"])
        inv = v["invoice_uri"]
        if cat not in data:
            data[cat] = {"category": cat, "count": 0, "invoices": set(), "suppliers": set()}
        data[cat]["count"]    += 1
        data[cat]["invoices"].add(inv)
        sup = supplier_map.get(inv)
        if sup:
            data[cat]["suppliers"].add(sup)

    result = []
    for cat, d in data.items():
        result.append({
            "category":        cat,
            "violationCount":  d["count"],
            "invoiceCount":    len(d["invoices"]),
            "supplierCount":   len(d["suppliers"]),
        })
    result.sort(key=lambda r: r["violationCount"], reverse=True)
    return result[:top_n]


def get_issues_by_section():
    """
    Map violations to invoice sections (Header, Supplier, Buyer, Line Items,
    Totals & Tax, Payment, Other) based on the resultPath / shape name.
    """
    SECTION_KEYWORDS = {
        "Header":     ["documentNumber","documentDate","documentType","orderNumber",
                        "belongsToProcess","deliveryDate","paymentCondition","supplierNote",
                        "hasDocumentFunction","hasDocumentNumber","documentDate"],
        "Supplier":   ["SupplierRole","PayeeRole","hasSupplier","hasPayee","supplier","Supplier"],
        "Buyer":      ["BuyerRole","InvoiceeRole","hasBuyer","hasInvoicee","buyer","Buyer"],
        "Line Items": ["Item","item","invoicedQuantity","GoodsPosition","GrossPrice",
                        "NetPrice","ArticleNumber","EAN","itemName","description",
                        "hasItem","hasInvoiceLine","quantity"],
        "Totals & Tax": ["TotalAmount","TotalLineItem","taxAmount","taxableAmount",
                          "VATrate","VATamount","vatRate","vatAmount","hasTax","hasTotal",
                          "hasTotalAmount","ChargeAmount","DiscountAmount","FreightCharge"],
        "Payment":    ["paymentCondition","TermsNetDueDate","dueDate","currency",
                        "invoiceCurrency"],
    }

    violations = _all_violations()

    section_data = {s: {"section": s, "violationCount": 0, "invoices": set()}
                    for s in list(SECTION_KEYWORDS.keys()) + ["Other"]}

    for v in violations:
        haystack = (v["path"] or "") + (v["shape"] or "")
        matched  = False
        for section, keywords in SECTION_KEYWORDS.items():
            if any(kw.lower() in haystack.lower() for kw in keywords):
                section_data[section]["violationCount"] += 1
                section_data[section]["invoices"].add(v["invoice_uri"])
                matched = True
                break
        if not matched:
            section_data["Other"]["violationCount"] += 1
            section_data["Other"]["invoices"].add(v["invoice_uri"])

    result = []
    for s, d in section_data.items():
        if d["violationCount"] > 0:
            result.append({
                "section":        s,
                "violationCount": d["violationCount"],
                "invoiceCount":   len(d["invoices"]),
            })
    result.sort(key=lambda r: r["violationCount"], reverse=True)
    return result


def get_issues_by_supplier(top_n=15):
    """Per-supplier breakdown of issue categories (for heatmap / bar chart)."""
    violations   = _all_violations()
    supplier_map = _supplier_names()

    # {supplier: {category: count}}
    data = {}
    for v in violations:
        sup = supplier_map.get(v["invoice_uri"], "Unknown")
        cat = _humanize(v["path"] or v["shape"])
        if sup not in data:
            data[sup] = {}
        data[sup][cat] = data[sup].get(cat, 0) + 1

    # Rank suppliers by total violation count
    ranked = sorted(data.items(), key=lambda x: sum(x[1].values()), reverse=True)[:top_n]

    result = []
    for sup, cat_counts in ranked:
        top_issues = sorted(cat_counts.items(), key=lambda x: x[1], reverse=True)[:5]
        result.append({
            "supplier":        sup,
            "totalViolations": sum(cat_counts.values()),
            "topCategories":   [{"category": cat, "count": cnt} for cat, cnt in top_issues],
        })
    return result


def get_severity_breakdown():
    """Violation counts grouped by sh:resultSeverity."""
    rows = _sparql(f"""
        SELECT ?sev (COUNT(?v) AS ?cnt)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v a <{SH}ValidationResult> .
            OPTIONAL {{ ?v <{SH}resultSeverity> ?sev }}
        }}
        GROUP BY ?sev
    """)
    result = []
    for b in rows:
        result.append({
            "severity": b["sev"]["value"] if b.get("sev") else "Unknown",
            "count":    int(b["cnt"]["value"]),
        })
    result.sort(key=lambda r: r["count"], reverse=True)
    return result


def get_severity_breakdown():
    """Violation counts by sh:resultSeverity."""
    rows = _sparql(f"""
        SELECT ?sev (COUNT(?v) AS ?c)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v a <{SH}ValidationResult> .
            OPTIONAL {{ ?v <{SH}resultSeverity> ?sev }}
        }}
        GROUP BY ?sev
        ORDER BY DESC(?c)
    """)
    result = []
    for b in rows:
        sev = _val(b, "sev") or "Unknown"
        result.append({"severity": _short(sev), "count": int(b["c"]["value"])})
    return result
