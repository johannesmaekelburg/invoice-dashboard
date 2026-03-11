from flask import Blueprint, jsonify
from functions.invoice_service import (
    get_invoice_summary,
    get_invoice_parties,
    get_invoice_items,
    get_violations_by_severity,
    get_violations_by_shape,
    get_violations_enriched,
    get_compliance_summary,
)

invoice_bp = Blueprint('invoice', __name__)


@invoice_bp.route('/invoice/summary', methods=['GET'])
def invoice_summary():
    return jsonify(get_invoice_summary())


@invoice_bp.route('/invoice/parties', methods=['GET'])
def invoice_parties():
    return jsonify(get_invoice_parties())


@invoice_bp.route('/invoice/items', methods=['GET'])
def invoice_items():
    return jsonify(get_invoice_items())


@invoice_bp.route('/invoice/violations/by-severity', methods=['GET'])
def violations_by_severity():
    return jsonify(get_violations_by_severity())


@invoice_bp.route('/invoice/violations/by-shape', methods=['GET'])
def violations_by_shape():
    return jsonify(get_violations_by_shape())


@invoice_bp.route('/invoice/violations/enriched', methods=['GET'])
def violations_enriched():
    return jsonify(get_violations_enriched())


@invoice_bp.route('/invoice/compliance', methods=['GET'])
def compliance_summary():
    return jsonify(get_compliance_summary())
