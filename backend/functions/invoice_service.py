import sys
import os
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
from config import ENDPOINT_URL, DATA_GRAPH_URI, VALIDATION_REPORT_URI, SHAPES_GRAPH_URI
from SPARQLWrapper import SPARQLWrapper, JSON

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
    sparql.setQuery(query)
    sparql.setReturnFormat(JSON)
    return sparql.query().convert()["results"]["bindings"]


def _val(b, k):
    return b[k]["value"] if k in b else None


def get_invoice_summary():
    """Get invoice header and financial details from the data graph."""
    rows = _sparql(f"""
        SELECT ?invoice ?docNumber ?docDate ?invoiceAmount ?taxableAmount
               ?totalLineItemAmount ?discountAmount ?taxAmount ?vatAmount
               ?vatRate ?currency ?paymentCondition ?dueDate ?deliveryDate
               ?process ?orderNumberBuyer ?docType ?docFunction
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            ?invoice a <{P2P_DOC}E-Invoice> .
            ?invoice <{EDIFACT}hasInvoiceDetails> ?details .
            OPTIONAL {{ ?details <{EDIFACT}hasDocumentNumber> ?docNumber }}
            OPTIONAL {{ ?details <{EDIFACT}documentDate> ?docDate }}
            OPTIONAL {{ ?details <{EDIFACT}hasInvoiceAmount> ?invoiceAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasTaxableAmount> ?taxableAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasTotalLineItemAmount> ?totalLineItemAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasDiscountAmount> ?discountAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasTaxAmount> ?taxAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasVATamount> ?vatAmount }}
            OPTIONAL {{ ?details <{EDIFACT}hasVATrate> ?vatRate }}
            OPTIONAL {{ ?details <{SCHEMA}currency> ?currency }}
            OPTIONAL {{ ?details <{EDIFACT}paymentCondition> ?paymentCondition }}
            OPTIONAL {{ ?details <{EDIFACT}hasTermsNetDueDate> ?dueDate }}
            OPTIONAL {{ ?details <{P2P_INV}actualDeliveryDate> ?deliveryDate }}
            OPTIONAL {{ ?invoice <{EDIFACT}belongsToProcess> ?process }}
            OPTIONAL {{ ?details <{EDIFACT}orderNumberBuyer> ?orderNumberBuyer }}
            OPTIONAL {{ ?details <{EDIFACT}hasDocumentType> ?docType }}
            OPTIONAL {{ ?details <{EDIFACT}hasDocumentFunction> ?docFunction }}
        }}
        LIMIT 1
    """)
    if not rows:
        return {}
    b = rows[0]
    return {
        "invoiceURI": _val(b, "invoice"),
        "documentNumber": _val(b, "docNumber"),
        "documentDate": _val(b, "docDate"),
        "invoiceAmount": _val(b, "invoiceAmount"),
        "taxableAmount": _val(b, "taxableAmount"),
        "totalLineItemAmount": _val(b, "totalLineItemAmount"),
        "discountAmount": _val(b, "discountAmount"),
        "taxAmount": _val(b, "taxAmount"),
        "vatAmount": _val(b, "vatAmount"),
        "vatRate": _val(b, "vatRate"),
        "currency": _val(b, "currency"),
        "paymentCondition": _val(b, "paymentCondition"),
        "dueDate": _val(b, "dueDate"),
        "deliveryDate": _val(b, "deliveryDate"),
        "process": _val(b, "process"),
        "orderNumberBuyer": _val(b, "orderNumberBuyer"),
        "documentType": _val(b, "docType"),
        "documentFunction": _val(b, "docFunction"),
    }


def get_invoice_parties():
    """Get all organizations and their roles from the data graph."""
    rows = _sparql(f"""
        SELECT DISTINCT ?org ?gln ?roleType
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            ?org a <{ORG}FormalOrganization> .
            OPTIONAL {{ ?org <{P2P_ORG}globalLocationNumber> ?gln }}
            OPTIONAL {{
                ?org <{AGENT_ROLE}performsAgentRole> ?roleURI .
                ?roleURI a ?roleType .
            }}
        }}
        ORDER BY ?org
    """)
    parties = {}
    for b in rows:
        org = b["org"]["value"]
        if org not in parties:
            parties[org] = {
                "uri": org,
                "id": org.split("/")[-1],
                "gln": _val(b, "gln"),
                "roles": [],
            }
        if "roleType" in b:
            role_uri = b["roleType"]["value"]
            role_label = role_uri.split("/")[-1]
            if role_label not in parties[org]["roles"]:
                parties[org]["roles"].append(role_label)
    return list(parties.values())


def get_invoice_items():
    """Get all line items from the data graph."""
    rows = _sparql(f"""
        SELECT ?item ?itemName ?grossPrice ?lineAmount ?quantity ?unit
               ?ean ?itemNumBuyer ?itemNumSupplier ?productId ?invoiceLine
        FROM <{DATA_GRAPH_URI}>
        WHERE {{
            ?item a <{P2P_ITEM}item> .
            OPTIONAL {{ ?item <{P2P_ITEM}itemName> ?itemName }}
            OPTIONAL {{ ?item <{EDIFACT}hasGrosspriceOfItem> ?grossPrice }}
            OPTIONAL {{ ?item <{EDIFACT}hasLineItemAmount> ?lineAmount }}
            OPTIONAL {{ ?item <{P2P_DOC_LINE}invoicedQuantity> ?quantity }}
            OPTIONAL {{ ?item <{EDIFACT}hasQuantityUnit> ?unit }}
            OPTIONAL {{ ?item <{EDIFACT}internationalArticleNumber> ?ean }}
            OPTIONAL {{ ?item <{EDIFACT}itemNumberBuyer> ?itemNumBuyer }}
            OPTIONAL {{ ?item <{EDIFACT}itemNumberSupplier> ?itemNumSupplier }}
            OPTIONAL {{ ?item <{EDIFACT}hasProductIdentification> ?productId }}
            OPTIONAL {{ ?item <{P2P_INV}hasInvoiceLine> ?invoiceLine }}
        }}
    """)
    return [{
        "uri": _val(b, "item"),
        "itemName": _val(b, "itemName"),
        "grossPrice": _val(b, "grossPrice"),
        "lineAmount": _val(b, "lineAmount"),
        "quantity": _val(b, "quantity"),
        "unit": _val(b, "unit"),
        "ean": _val(b, "ean"),
        "itemNumberBuyer": _val(b, "itemNumBuyer"),
        "itemNumberSupplier": _val(b, "itemNumSupplier"),
        "productId": _val(b, "productId"),
        "invoiceLine": _val(b, "invoiceLine"),
    } for b in rows]


def get_violations_by_severity():
    """Get violation counts grouped by severity."""
    rows = _sparql(f"""
        SELECT ?severity (COUNT(?v) AS ?count)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v a <{SH}ValidationResult> .
            ?v <{SH}resultSeverity> ?severity .
        }}
        GROUP BY ?severity
        ORDER BY DESC(?count)
    """)
    return [{
        "severity": b["severity"]["value"].split("#")[-1],
        "severityURI": b["severity"]["value"],
        "count": int(b["count"]["value"]),
    } for b in rows]


def get_violations_by_shape():
    """Get violations grouped by source shape and severity."""
    rows = _sparql(f"""
        SELECT ?sourceShape ?severity ?shapePath (COUNT(?v) AS ?count)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v a <{SH}ValidationResult> .
            ?v <{SH}sourceShape> ?sourceShape .
            ?v <{SH}resultSeverity> ?severity .
            FILTER(isIRI(?sourceShape))
            OPTIONAL {{ ?sourceShape <{SH}path> ?shapePath }}
        }}
        GROUP BY ?sourceShape ?severity ?shapePath
        ORDER BY DESC(?count)
    """)
    results = []
    for b in rows:
        shape = b["sourceShape"]["value"]
        shape_path = _val(b, "shapePath")
        if shape_path:
            # Anonymous property shape — label by the path it constrains
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


def get_violations_enriched():
    """
    Get all violations with enriched context: violation details + actual values
    present in the data graph for the affected focus node and result path.
    """
    rows = _sparql(f"""
        SELECT ?v ?focusNode ?resultPath ?severity ?constraintComponent ?message ?value ?sourceShape
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
        }}
        ORDER BY ?severity ?focusNode
    """)

    enriched = []
    for b in rows:
        focus_node = b["focusNode"]["value"]
        result_path = _val(b, "resultPath")

        # Look up actual values present in the data graph for this path on this focus node
        actual_values = []
        if result_path:
            try:
                actual_rows = _sparql(f"""
                    SELECT ?val
                    FROM <{DATA_GRAPH_URI}>
                    WHERE {{ <{focus_node}> <{result_path}> ?val . }}
                """)
                actual_values = [r["val"]["value"] for r in actual_rows]
            except Exception:
                pass

        # Get what type the focus node is
        focus_type = None
        try:
            type_rows = _sparql(f"""
                SELECT ?type
                FROM <{DATA_GRAPH_URI}>
                WHERE {{
                    <{focus_node}> a ?type .
                    FILTER(?type != <http://www.w3.org/2002/07/owl#NamedIndividual>)
                }}
                LIMIT 1
            """)
            if type_rows:
                focus_type = type_rows[0]["type"]["value"]
        except Exception:
            pass

        source_shape = _val(b, "sourceShape") or ""
        if result_path and (not source_shape or "genid" in source_shape):
            # Anonymous property shape — use the constrained path as label
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
            "resultPathShort": result_path.split("/")[-1] if result_path else None,
            "severity": b["severity"]["value"].split("#")[-1],
            "constraintComponent": b["constraintComponent"]["value"].split("#")[-1],
            "message": _val(b, "message"),
            "foundValue": _val(b, "value"),
            "actualValuesInData": actual_values,
            "sourceShape": source_shape,
            "shapeName": shape_name,
        })

    return enriched


def get_compliance_summary():
    """Overall compliance summary: totals, by severity, affected nodes/paths."""
    total_rows = _sparql(f"""
        SELECT (COUNT(?v) AS ?total)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{ ?v a <{SH}ValidationResult> . }}
    """)
    total = int(total_rows[0]["total"]["value"]) if total_rows else 0

    affected_nodes_rows = _sparql(f"""
        SELECT (COUNT(DISTINCT ?fn) AS ?c)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{ ?v <{SH}focusNode> ?fn . }}
    """)
    affected_nodes = int(affected_nodes_rows[0]["c"]["value"]) if affected_nodes_rows else 0

    affected_paths_rows = _sparql(f"""
        SELECT (COUNT(DISTINCT ?p) AS ?c)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{ ?v <{SH}resultPath> ?p . }}
    """)
    affected_paths = int(affected_paths_rows[0]["c"]["value"]) if affected_paths_rows else 0

    named_shapes_rows = _sparql(f"""
        SELECT (COUNT(DISTINCT ?s) AS ?c)
        FROM <{VALIDATION_REPORT_URI}>
        WHERE {{
            ?v <{SH}sourceShape> ?s .
            FILTER(isIRI(?s))
        }}
    """)
    affected_shapes = int(named_shapes_rows[0]["c"]["value"]) if named_shapes_rows else 0

    return {
        "conforms": total == 0,
        "totalViolations": total,
        "bySeverity": get_violations_by_severity(),
        "affectedFocusNodes": affected_nodes,
        "affectedPaths": affected_paths,
        "affectedShapes": affected_shapes,
    }
