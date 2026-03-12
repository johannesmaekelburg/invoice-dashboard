from flask import Blueprint, jsonify, request
from functions.invoice_service import (
    get_invoice_list,
    get_invoice_summary,
    get_invoice_parties,
    get_invoice_items,
    get_violations_by_shape,
    get_violations_enriched,
    get_compliance_summary,
    get_global_stats,
    get_invoice_detail,
)

invoice_bp = Blueprint('invoice', __name__)


def _require_uri():
    """Return the invoice_uri param, or raise a 400 response."""
    uri = request.args.get('invoice_uri', '').strip()
    if not uri:
        from flask import abort
        abort(400, description='invoice_uri query parameter is required')
    return uri


@invoice_bp.route('/invoice/list', methods=['GET'])
def invoice_list():
    return jsonify(get_invoice_list())


@invoice_bp.route('/invoice/global-stats', methods=['GET'])
def global_stats():
    return jsonify(get_global_stats())


@invoice_bp.route('/invoice/detail', methods=['GET'])
def invoice_detail():
    return jsonify(get_invoice_detail(_require_uri()))


@invoice_bp.route('/invoice/summary', methods=['GET'])
def invoice_summary():
    return jsonify(get_invoice_summary(_require_uri()))


@invoice_bp.route('/invoice/parties', methods=['GET'])
def invoice_parties():
    return jsonify(get_invoice_parties(_require_uri()))


@invoice_bp.route('/invoice/items', methods=['GET'])
def invoice_items():
    return jsonify(get_invoice_items(_require_uri()))


@invoice_bp.route('/invoice/violations/by-shape', methods=['GET'])
def violations_by_shape():
    invoice_uri = request.args.get('invoice_uri') or None
    return jsonify(get_violations_by_shape(invoice_uri))


@invoice_bp.route('/invoice/violations/enriched', methods=['GET'])
def violations_enriched():
    invoice_uri = request.args.get('invoice_uri') or None
    limit = int(request.args.get('limit', 500))
    return jsonify(get_violations_enriched(invoice_uri, limit))


@invoice_bp.route('/invoice/compliance', methods=['GET'])
def compliance_summary():
    invoice_uri = request.args.get('invoice_uri') or None
    return jsonify(get_compliance_summary(invoice_uri))
