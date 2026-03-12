import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ENDPOINT_URL, DATA_GRAPH_URI, VALIDATION_REPORT_URI, SHAPES_GRAPH_URI
from SPARQLWrapper import SPARQLWrapper, JSON, POST
from concurrent.futures import ThreadPoolExecutor

SH = "http://www.w3.org/ns/shacl#"
EDIFACT = "https://purl.org/edifact/ontology#"
P2P_INV = "https://purl.org/p2p-o/invoice#"
P2P_DOC = "https://purl.org/p2p-o/document#"
P2P_ITEM = "https://purl.org/p2p-o/item#"
P2P_ORG = "https://purl.org/p2p-o/organization#"
P2P_DOC_LINE = "https://purl.org/p2p-o/documentline#"
AGENT_ROLE = "https://archive.org/services/purl/domain/modular_ontology_design_library/agentrole#"
ORG = "http://www.w3.org/ns/org#"
SCHEMA = "http://schema.org/"


def _sparql(query):
    sparql = SPARQLWrapper(ENDPOINT_URL)
    sparql.setMethod(POST)
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()["results"]["bindings"]


def _val(b, k):
    return b[k]["value"] if k in b else None


def _get_related_nodes(invoice_uri):
    """Return data-instance IRIs reachable from an E-Invoice in 0-2 hops.

    Filters out well-known ontology/schema namespaces so only instance nodes
    (typically http://example.com/…) are returned.  This keeps the VALUES
    clause small (< 100 items) so Virtuoso never hits its query-length limit.
    """
    # Derive the instance-node base URL from the invoice URI itself.
    # e.g. "http://example.com/-999" → base = "http://example.com/"
    base = invoice_uri.rsplit('/', 1)[0] + "/"
    rows = _sparql(f"""
        SELECT DISTINCT ?node
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            {{ BIND(<{invoice_uri}> AS ?node) }}
            UNION
            {{
                <{invoice_uri}> ?p ?node .
                FILTER(isIRI(?node) && STRSTARTS(STR(?node), "{base}"))
            }}
            UNION
            {{
                <{invoice_uri}> ?p ?mid .
                FILTER(isIRI(?mid) && STRSTARTS(STR(?mid), "{base}"))
                ?mid ?p2 ?node .
                FILTER(isIRI(?node) && STRSTARTS(STR(?node), "{base}"))
            }}
        }}
        LIMIT 200
    """)
    return [b["node"]["value"] for b in rows]


def _focus_node_filter(nodes):
    """Build a SPARQL VALUES clause to restrict ?focusNode, or '' for no filter."""
    if not nodes:
        return ""
    values_str = " ".join(f"<{n}>" for n in nodes)
    return f"VALUES ?focusNode {{ {values_str} }}"


# ---------------------------------------------------------------------------
# Invoice list (all E-Invoices in the DataGraph)
# ---------------------------------------------------------------------------

def get_invoice_list():
    """Return all E-Invoice entities with key metadata and their violation counts.

    Uses two queries:
    1. Fetch invoice metadata from DataGraph.
    2. A single cross-graph aggregation that counts violations per invoice via
       a 2-hop join (invoice → 1-hop nodes → 2-hop nodes), without VALUES clauses.
    """
    # --- Query 1: invoice metadata ---
    rows = _sparql(f"""
        SELECT DISTINCT ?invoice ?docNumber ?docDate ?docType ?invoiceAmount ?currency
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            ?invoice a <{P2P_DOC}E-Invoice> .
            OPTIONAL {{
                ?invoice <{EDIFACT}hasInvoiceDetails> ?details .
                OPTIONAL {{ ?details <{EDIFACT}hasDocumentNumber> ?docNumber }}
                OPTIONAL {{ ?details <{EDIFACT}documentDate> ?docDate }}
                OPTIONAL {{ ?details <{EDIFACT}hasDocumentType> ?docType }}
                OPTIONAL {{ ?details <{EDIFACT}hasInvoiceAmount> ?invAmt1 }}
                OPTIONAL {{ ?details <{EDIFACT}hasTotalAmountMessage> ?invAmt2 }}
                BIND(COALESCE(?invAmt1, ?invAmt2) AS ?invoiceAmount)
                OPTIONAL {{ ?details <{SCHEMA}currency> ?currency }}
            }}
        }}
        ORDER BY ?invoice
    """)

    # --- Query 2: violation counts per focusNode (single graph, no joins, fast) ---
    viol_rows = _sparql(f"""
        SELECT ?focusNode (COUNT(DISTINCT ?v) AS ?count)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v a <{SH}ValidationResult> ;
               <{SH}focusNode> ?focusNode .
        }}
        GROUP BY ?focusNode
    """)
    focus_counts = {b["focusNode"]["value"]: int(b["count"]["value"]) for b in viol_rows}

    # --- Query 3: map violation focusNodes → parent E-Invoice via VALUES lookup ---
    # Uses VALUES to restrict traversal to only IRIs that actually have violations,
    # avoiding the full cross-graph expansion that caused the Virtuoso timeout.
    # Chunked at 500 items to keep query strings manageable.
    count_map = {}
    if focus_counts:
        focus_list = list(focus_counts.keys())
        CHUNK = 80
        for i in range(0, len(focus_list), CHUNK):
            chunk = focus_list[i : i + CHUNK]
            values_str = " ".join(f"<{fn}>" for fn in chunk)
            assoc_rows = _sparql(f"""
                SELECT DISTINCT ?invoice ?fn
                FROM <{DATA_GRAPH_URI}>
                WHERE {{
                    VALUES ?fn {{ {values_str} }}
                    {{
                        ?fn a <{P2P_DOC}E-Invoice> .
                        BIND(?fn AS ?invoice)
                    }} UNION {{
                        ?invoice a <{P2P_DOC}E-Invoice> .
                        ?invoice ?p ?fn .
                    }} UNION {{
                        ?invoice a <{P2P_DOC}E-Invoice> .
                        ?invoice ?p1 ?mid .
                        ?mid ?p2 ?fn .
                    }}
                }}
            """)
            for b in assoc_rows:
                inv = b["invoice"]["value"]
                fn_uri = b["fn"]["value"]
                count_map[inv] = count_map.get(inv, 0) + focus_counts.get(fn_uri, 0)

    # --- Query 4: supplier / buyer names per invoice ---
    # supplierName: try SupplierRole directly (msg_0014), else PayeeRole (msg_0026)
    # buyerName:    try BuyerRole directly, else InvoiceeRole (both datasets)
    party_name_rows = _sparql(f"""
        SELECT ?invoice ?supplierName ?buyerName
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            ?invoice a <{P2P_DOC}E-Invoice> .
            OPTIONAL {{
                ?invoice <{P2P_INV}hasSupplier> ?sup .
                OPTIONAL {{ ?sup <{P2P_ORG}formalName> ?supDirect }}
            }}
            OPTIONAL {{
                ?invoice <{P2P_INV}hasPayee> ?payee .
                OPTIONAL {{ ?payee <{P2P_ORG}formalName> ?supViaPayee }}
            }}
            BIND(COALESCE(?supDirect, ?supViaPayee) AS ?supplierName)
            OPTIONAL {{
                ?invoice <{P2P_INV}hasBuyer> ?byr .
                OPTIONAL {{ ?byr <{P2P_ORG}formalName> ?byrDirect }}
            }}
            OPTIONAL {{
                ?invoice <{EDIFACT}hasInvoicee> ?invee .
                OPTIONAL {{ ?invee <{P2P_ORG}formalName> ?byrViaInvoicee }}
            }}
            BIND(COALESCE(?byrDirect, ?byrViaInvoicee) AS ?buyerName)
        }}
    """)
    party_name_map = {}
    for b in party_name_rows:
        inv = b["invoice"]["value"]
        party_name_map[inv] = {
            "supplierName": _val(b, "supplierName"),
            "buyerName":    _val(b, "buyerName"),
        }

    invoices = []
    for b in rows:
        invoice_uri = b["invoice"]["value"]
        pnames = party_name_map.get(invoice_uri, {})
        invoices.append({
            "uri": invoice_uri,
            "id": invoice_uri.split("/")[-1],
            "documentNumber": _val(b, "docNumber"),
            "documentDate": _val(b, "docDate"),
            "documentType": _val(b, "docType"),
            "invoiceAmount": _val(b, "invoiceAmount"),
            "currency": _val(b, "currency"),
            "violationCount": count_map.get(invoice_uri, 0),
            "supplierName": pnames.get("supplierName"),
            "buyerName":    pnames.get("buyerName"),
        })
    return invoices


# ---------------------------------------------------------------------------
# Per-invoice detail endpoints
# ---------------------------------------------------------------------------

def get_invoice_summary(invoice_uri):
    """Get invoice header and financial details for a specific E-Invoice."""
    rows = _sparql(f"""
        SELECT ?docNumber ?docDate ?invoiceAmount ?taxableAmount
               ?totalLineItemAmount ?discountAmount ?taxAmount ?vatAmount
               ?vatRate ?currency ?invoiceCurrency ?paymentCondition ?dueDate
               ?deliveryDate ?deliveryCondition ?process ?orderNumberBuyer
               ?dateOrderNumberBuyer ?docType ?docFunction
               ?chargeAmount ?chargeReason ?freightCharge ?supplierNote
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            <{invoice_uri}> <{EDIFACT}hasInvoiceDetails> ?details .
            OPTIONAL {{ ?details <{EDIFACT}hasDocumentNumber> ?docNumber }}
            OPTIONAL {{ ?details <{EDIFACT}documentDate> ?docDate }}
            OPTIONAL {{ ?details <{EDIFACT}hasInvoiceAmount> ?invAmt1 }}
            OPTIONAL {{ ?details <{EDIFACT}hasTotalAmountMessage> ?invAmt2 }}
            BIND(COALESCE(?invAmt1, ?invAmt2) AS ?invoiceAmount)
            OPTIONAL {{ ?details <{EDIFACT}hasTaxableAmount> ?taxableAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasTotalLineItemAmount> ?totalLineItemAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasDiscountAmount> ?discountAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasTaxAmount> ?taxAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasVATamount> ?vatAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasVATrate> ?vatRate }}
            OPTIONAL {{ ?details <{SCHEMA}currency> ?currency }}
            OPTIONAL {{ ?details <{EDIFACT}invoiceCurrency> ?invoiceCurrency }}
            OPTIONAL {{ ?details <{EDIFACT}paymentCondition> ?paymentCondition }}
            OPTIONAL {{ ?details <{EDIFACT}hasTermsNetDueDate> ?dueDate }}
            OPTIONAL {{ ?details <{EDIFACT}actualDeliveryDate> ?deliveryDate }}
            OPTIONAL {{ ?details <{EDIFACT}deliveryCondition> ?deliveryCondition }}
            OPTIONAL {{ <{invoice_uri}> <{EDIFACT}belongsToProcess> ?process }}
            OPTIONAL {{ ?details <{EDIFACT}orderNumberBuyer> ?orderNumberBuyer }}
            OPTIONAL {{ ?details <{EDIFACT}dateOrderNumberBuyer> ?dateOrderNumberBuyer }}
            OPTIONAL {{ ?details <{EDIFACT}hasDocumentType> ?docType }}
            OPTIONAL {{ ?details <{EDIFACT}hasDocumentFunction> ?docFunction }}
            OPTIONAL {{ ?details <{EDIFACT}hasChargeAmount> ?chargeAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasChargeReason> ?chargeReason }}
            OPTIONAL {{ ?details <{EDIFACT}hasFreightCharge> ?freightCharge }}
            OPTIONAL {{ ?details <{EDIFACT}supplierNote> ?supplierNote }}
        }}
        LIMIT 1
    """)
    if not rows:
        return {}
    b = rows[0]
    return {
        "invoiceURI": invoice_uri,
        "documentNumber": _val(b, "docNumber"),
        "documentDate": _val(b, "docDate"),
        "documentType": _val(b, "docType"),
        "documentFunction": _val(b, "docFunction"),
        "process": _val(b, "process"),
        "orderNumberBuyer": _val(b, "orderNumberBuyer"),
        "dateOrderNumberBuyer": _val(b, "dateOrderNumberBuyer"),
        "deliveryDate": _val(b, "deliveryDate"),
        "deliveryCondition": _val(b, "deliveryCondition"),
        "paymentCondition": _val(b, "paymentCondition"),
        "dueDate": _val(b, "dueDate"),
        "supplierNote": _val(b, "supplierNote"),
        "invoiceAmount": _val(b, "invoiceAmount"),
        "taxableAmount": _val(b, "taxableAmount"),
        "totalLineItemAmount": _val(b, "totalLineItemAmount"),
        "discountAmount": _val(b, "discountAmount"),
        "taxAmount": _val(b, "taxAmount"),
        "vatAmount": _val(b, "vatAmount"),
        "vatRate": _val(b, "vatRate"),
        "currency": _val(b, "currency"),
        "invoiceCurrency": _val(b, "invoiceCurrency"),
        "chargeAmount": _val(b, "chargeAmount"),
        "chargeReason": _val(b, "chargeReason"),
        "freightCharge": _val(b, "freightCharge"),
    }


def get_invoice_parties(invoice_uri):
    """Get parties related to a specific E-Invoice via role instance nodes.

    The party data (name, GLN, address, etc.) lives directly on the role
    instance nodes (SupplierRole, BuyerRole, DeliveryPartyRole, InvoiceeRole)
    that are reachable via hasSupplier / hasBuyer / hasDeliveryParty /
    hasInvoicee from the invoice.
    """
    VCARD = "http://www.w3.org/2006/vcard/ns#"
    FRAPO = "http://purl.org/cerif/frapo/"
    base = invoice_uri.rsplit("/", 1)[0] + "/"

    rows = _sparql(f"""
        SELECT DISTINCT ?role ?roleType ?name ?gln ?vat ?city ?country
                        ?countryCode ?street ?postalCode ?contact ?phone
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            <{invoice_uri}> ?rolePred ?role .
            FILTER(?rolePred IN (
                <{P2P_INV}hasBuyer>,
                <{P2P_INV}hasSupplier>,
                <{P2P_INV}hasPayee>,
                <{EDIFACT}hasDeliveryParty>,
                <{EDIFACT}hasInvoicee>
            ))
            OPTIONAL {{
                ?role a ?roleType .
                FILTER(STRSTARTS(STR(?roleType), "{base}"))
            }}
            OPTIONAL {{ ?role <{P2P_ORG}formalName> ?name }}
            OPTIONAL {{ ?role <{P2P_ORG}globalLocationNumber> ?gln }}
            OPTIONAL {{ ?role <{P2P_ORG}VATIdentifier> ?vat }}
            OPTIONAL {{ ?role <{EDIFACT}hasCity> ?city }}
            OPTIONAL {{ ?role <{EDIFACT}hasCountry> ?country }}
            OPTIONAL {{ ?role <{FRAPO}hasCountryCode> ?countryCode }}
            OPTIONAL {{ ?role <{VCARD}hasStreetAddress> ?street }}
            OPTIONAL {{ ?role <{VCARD}postalCode> ?postalCode }}
            OPTIONAL {{ ?role <{EDIFACT}contactDepartmentPerson> ?contact }}
            OPTIONAL {{ ?role <{EDIFACT}contactPersonTelefonNumber> ?phone }}
        }}
        ORDER BY ?role
    """)

    parties = {}
    for b in rows:
        role = b["role"]["value"]
        if role not in parties:
            parties[role] = {
                "uri": role,
                "id": role.split("/")[-1],
                "name": _val(b, "name"),
                "gln": _val(b, "gln"),
                "vat": _val(b, "vat"),
                "city": _val(b, "city"),
                "country": _val(b, "country"),
                "countryCode": _val(b, "countryCode"),
                "street": _val(b, "street"),
                "postalCode": _val(b, "postalCode"),
                "contact": _val(b, "contact"),
                "phone": _val(b, "phone"),
                "roles": [],
            }
        if "roleType" in b:
            role_label = b["roleType"]["value"].split("/")[-1]
            if role_label not in parties[role]["roles"]:
                parties[role]["roles"].append(role_label)
    return list(parties.values())


def get_invoice_items(invoice_uri):
    """Get line items belonging to a specific E-Invoice."""
    rows = _sparql(f"""
        SELECT ?item ?itemName ?description ?grossPrice ?netPrice
               ?totalGoodsPosition ?quantity ?unit ?vatRate
               ?ean ?partNumberBuyer ?itemNumSupplier ?productId
               ?allowanceAmount ?allowanceReason ?allowancePercentage
               ?invoiceLine ?deliveryNoteNumber
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            <{invoice_uri}> <{EDIFACT}hasItem> ?item .
            ?item a <{P2P_ITEM}item> .
            OPTIONAL {{ ?item <{P2P_ITEM}itemName> ?itemName }}
            OPTIONAL {{ ?item <{EDIFACT}descriptionOfGoods> ?description }}
            OPTIONAL {{ ?item <{EDIFACT}hasGrosspriceOfItem> ?grossPrice }}
            OPTIONAL {{ ?item <{EDIFACT}hasNetpriceOfItem> ?netPrice }}
            OPTIONAL {{ ?item <{EDIFACT}hasTotalGoodsPosition> ?totalGoodsPosition }}
            OPTIONAL {{ ?item <{P2P_DOC_LINE}invoicedQuantity> ?quantity }}
            OPTIONAL {{ ?item <{EDIFACT}hasQuantityUnit> ?unit }}
            OPTIONAL {{ ?item <{EDIFACT}hasVATrate> ?vatRate }}
            OPTIONAL {{ ?item <{EDIFACT}internationalArticleNumber> ?ean }}
            OPTIONAL {{ ?item <{EDIFACT}partNumberBuyer> ?partNumberBuyer }}
            OPTIONAL {{ ?item <{EDIFACT}itemNumberSupplier> ?itemNumSupplier }}
            OPTIONAL {{ ?item <{EDIFACT}hasProductIdentification> ?productId }}
            OPTIONAL {{ ?item <{EDIFACT}hasAllowanceAmount> ?allowanceAmount }}
            OPTIONAL {{ ?item <{EDIFACT}hasAllowanceReason> ?allowanceReason }}
            OPTIONAL {{ ?item <{EDIFACT}hasAllowancePercentage> ?allowancePercentage }}
            OPTIONAL {{ ?item <{P2P_INV}hasInvoiceLine> ?invoiceLine }}
            OPTIONAL {{ ?item <{EDIFACT}deliveryNoteNumber> ?deliveryNoteNumber }}
        }}
    """)
    return [{
        "uri": _val(b, "item"),
        "itemName": _val(b, "itemName"),
        "description": _val(b, "description"),
        "grossPrice": _val(b, "grossPrice"),
        "netPrice": _val(b, "netPrice"),
        "totalGoodsPosition": _val(b, "totalGoodsPosition"),
        "quantity": _val(b, "quantity"),
        "unit": _val(b, "unit"),
        "vatRate": _val(b, "vatRate"),
        "ean": _val(b, "ean"),
        "partNumberBuyer": _val(b, "partNumberBuyer"),
        "itemNumberSupplier": _val(b, "itemNumSupplier"),
        "productId": _val(b, "productId"),
        "allowanceAmount": _val(b, "allowanceAmount"),
        "allowanceReason": _val(b, "allowanceReason"),
        "allowancePercentage": _val(b, "allowancePercentage"),
        "invoiceLine": _val(b, "invoiceLine"),
        "deliveryNoteNumber": _val(b, "deliveryNoteNumber"),
    } for b in rows]


def get_violations_by_shape(invoice_uri=None, nodes=None):
    """Get violations grouped by source shape and severity, optionally for one invoice."""
    if nodes is None:
        nodes = _get_related_nodes(invoice_uri) if invoice_uri else []
    fn_filter = _focus_node_filter(nodes)

    rows = _sparql(f"""
        SELECT ?sourceShape ?severity ?shapePath (COUNT(?v) AS ?count)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v a <{SH}ValidationResult> .
            ?v <{SH}focusNode> ?focusNode .
            ?v <{SH}sourceShape> ?sourceShape .
            ?v <{SH}resultSeverity> ?severity .
            FILTER(isIRI(?sourceShape))
            OPTIONAL {{ ?sourceShape <{SH}path> ?shapePath }}
            {fn_filter}
        }}
        GROUP BY ?sourceShape ?severity ?shapePath
        ORDER BY DESC(?count)
    """)

    results = []
    for b in rows:
        shape = b["sourceShape"]["value"]
        shape_path = _val(b, "shapePath")
        if shape_path:
            shape_name = shape_path.split("/")[-1].split("#")[-1]
        elif "genid" in shape:
            shape_name = "(anonymous)"
        else:
            shape_name = shape.split("/")[-1]
        results.append({
            "shape": shape,
            "shapeName": shape_name,
            "severity": b["severity"]["value"].split("#")[-1],
            "count": int(b["count"]["value"]),
        })
    return results


def get_violations_enriched(invoice_uri=None, limit=500, nodes=None):
    """
    Get violations enriched with actual data graph values.
    Uses batched SPARQL lookups to avoid N+1 query problems.
    Optionally scoped to a single invoice.
    """
    if nodes is None:
        nodes = _get_related_nodes(invoice_uri) if invoice_uri else []
    fn_filter = _focus_node_filter(nodes)

    rows = _sparql(f"""
        SELECT ?focusNode ?resultPath ?severity ?constraintComponent ?message ?value ?sourceShape
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v a <{SH}ValidationResult> .
            ?v <{SH}focusNode> ?focusNode .
            ?v <{SH}resultSeverity> ?severity .
            ?v <{SH}sourceConstraintComponent> ?constraintComponent .
            OPTIONAL {{ ?v <{SH}resultPath> ?resultPath }}
            OPTIONAL {{ ?v <{SH}resultMessage> ?message }}
            OPTIONAL {{ ?v <{SH}value> ?value }}
            OPTIONAL {{ ?v <{SH}sourceShape> ?sourceShape }}
            {fn_filter}
        }}
        ORDER BY ?severity ?focusNode
        LIMIT {limit}
    """)

    if not rows:
        return []

    # Batch 1: get rdf:type for all unique focus nodes
    unique_nodes = list(set(b["focusNode"]["value"] for b in rows))
    type_map = {}
    if unique_nodes:
        nv = " ".join(f"<{n}>" for n in unique_nodes)
        type_rows = _sparql(f"""
            SELECT ?fn ?type
            FROM <{DATA_GRAPH_URI}>
            WHERE {{
                ?fn a ?type .
                FILTER(?type != <http://www.w3.org/2002/07/owl#NamedIndividual>)
                VALUES ?fn {{ {nv} }}
            }}
        """)
        for tr in type_rows:
            fn = tr["fn"]["value"]
            if fn not in type_map:
                type_map[fn] = tr["type"]["value"]

    # Batch 2: get all properties of those focus nodes (to resolve actual values)
    props_map = {}  # fn → {predicate → [values]}
    if unique_nodes:
        nv = " ".join(f"<{n}>" for n in unique_nodes)
        prop_rows = _sparql(f"""
            SELECT ?fn ?p ?o
            FROM <{DATA_GRAPH_URI}>
            WHERE {{
                ?fn ?p ?o .
                VALUES ?fn {{ {nv} }}
            }}
        """)
        for pr in prop_rows:
            fn = pr["fn"]["value"]
            p = pr["p"]["value"]
            o = pr["o"]["value"]
            props_map.setdefault(fn, {}).setdefault(p, []).append(o)

    enriched = []
    for b in rows:
        focus_node = b["focusNode"]["value"]
        result_path = _val(b, "resultPath")
        source_shape = _val(b, "sourceShape") or ""
        focus_type = type_map.get(focus_node)
        actual_values = props_map.get(focus_node, {}).get(result_path, []) if result_path else []

        if result_path and (not source_shape or "genid" in source_shape):
            shape_name = result_path.split("/")[-1].split("#")[-1]
        elif source_shape:
            shape_name = source_shape.split("/")[-1]
        else:
            shape_name = "(anonymous)"

        enriched.append({
            "focusNode": focus_node,
            "focusNodeShort": focus_node.split("/")[-1],
            "focusNodeType": focus_type,
            "focusNodeTypeShort": focus_type.split("/")[-1] if focus_type else None,
            "resultPath": result_path,
            "resultPathShort": result_path.split("/")[-1].split("#")[-1] if result_path else None,
            "severity": b["severity"]["value"].split("#")[-1],
            "constraintComponent": b["constraintComponent"]["value"].split("#")[-1],
            "message": _val(b, "message"),
            "foundValue": _val(b, "value"),
            "actualValuesInData": actual_values,
            "sourceShape": source_shape,
            "shapeName": shape_name,
        })
    return enriched


def get_compliance_summary(invoice_uri=None, nodes=None):
    """Compliance totals, optionally scoped to one invoice."""
    if nodes is None:
        nodes = _get_related_nodes(invoice_uri) if invoice_uri else []
    fn_filter = _focus_node_filter(nodes)

    # Query 1: severity breakdown — total is derived in Python by summing counts
    sev_rows = _sparql(f"""
        SELECT ?severity (COUNT(?v) AS ?count)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v a <{SH}ValidationResult> .
            ?v <{SH}focusNode> ?focusNode .
            ?v <{SH}resultSeverity> ?severity .
            {fn_filter}
        }}
        GROUP BY ?severity
        ORDER BY DESC(?count)
    """)
    by_severity = [{
        "severity": b["severity"]["value"].split("#")[-1],
        "count": int(b["count"]["value"]),
    } for b in sev_rows]
    total = sum(s["count"] for s in by_severity)

    # Query 2: affected focus nodes + affected paths in one shot
    cnt_rows = _sparql(f"""
        SELECT (COUNT(DISTINCT ?focusNode) AS ?nodeCount)
               (COUNT(DISTINCT ?p) AS ?pathCount)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v <{SH}focusNode> ?focusNode .
            OPTIONAL {{ ?v <{SH}resultPath> ?p }}
            {fn_filter}
        }}
    """)

    return {
        "conforms": total == 0,
        "totalViolations": total,
        "bySeverity": by_severity,
        "affectedFocusNodes": int(cnt_rows[0]["nodeCount"]["value"]) if cnt_rows else 0,
        "affectedPaths": int(cnt_rows[0]["pathCount"]["value"]) if cnt_rows else 0,
    }


def get_invoice_detail(invoice_uri):
    """Return all per-invoice data in one call.

    Calls _get_related_nodes once and shares the result across all
    violation/compliance functions. Runs independent queries in parallel
    threads to minimise wall-clock time.
    """
    nodes = _get_related_nodes(invoice_uri)

    def _safe(future, default):
        try:
            return future.result()
        except Exception:
            return default

    with ThreadPoolExecutor(max_workers=5) as ex:
        f_summary    = ex.submit(get_invoice_summary, invoice_uri)
        f_parties    = ex.submit(get_invoice_parties, invoice_uri)
        f_items      = ex.submit(get_invoice_items, invoice_uri)
        f_shapes     = ex.submit(get_violations_by_shape, invoice_uri, nodes)
        f_enriched   = ex.submit(get_violations_enriched, invoice_uri, 500, nodes)
        f_compliance = ex.submit(get_compliance_summary, invoice_uri, nodes)

    return {
        "summary":         _safe(f_summary,    {}),
        "parties":         _safe(f_parties,    []),
        "items":           _safe(f_items,      []),
        "violationsByShape": _safe(f_shapes,   []),
        "violations":      _safe(f_enriched,   []),
        "compliance":      _safe(f_compliance, {
            "conforms": True, "totalViolations": 0,
            "bySeverity": [], "affectedFocusNodes": 0, "affectedPaths": 0,
        }),
    }


def get_global_stats():
    """Aggregate stats for the home page across all invoices/violations."""
    invoice_rows = _sparql(f"""
        SELECT (COUNT(DISTINCT ?inv) AS ?c)
        FROM <{DATA_GRAPH_URI}>
        WHERE {{ ?inv a <{P2P_DOC}E-Invoice> . }}
    """)
    item_rows = _sparql(f"""
        SELECT (COUNT(DISTINCT ?item) AS ?c)
        FROM <{DATA_GRAPH_URI}>
        WHERE {{ ?item a <{P2P_ITEM}item> . }}
    """)
    party_rows = _sparql(f"""
        SELECT (COUNT(DISTINCT ?org) AS ?c)
        FROM <{DATA_GRAPH_URI}>
        WHERE {{ ?org a <{ORG}FormalOrganization> . }}
    """)
    violation_rows = _sparql(f"""
        SELECT (COUNT(?v) AS ?c)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{ ?v a <{SH}ValidationResult> . }}
    """)
    sev_rows = _sparql(f"""
        SELECT ?severity (COUNT(?v) AS ?count)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v a <{SH}ValidationResult> .
            ?v <{SH}resultSeverity> ?severity .
        }}
        GROUP BY ?severity
        ORDER BY DESC(?count)
    """)
    return {
        "totalInvoices": int(invoice_rows[0]["c"]["value"]) if invoice_rows else 0,
        "totalItems": int(item_rows[0]["c"]["value"]) if item_rows else 0,
        "totalParties": int(party_rows[0]["c"]["value"]) if party_rows else 0,
        "totalViolations": int(violation_rows[0]["c"]["value"]) if violation_rows else 0,
        "bySeverity": [{
            "severity": b["severity"]["value"].split("#")[-1],
            "count": int(b["count"]["value"]),
        } for b in sev_rows],
    }
