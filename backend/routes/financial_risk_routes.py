from flask import Blueprint, jsonify
from functions.financial_risk_service import (
    get_financial_risk_summary,
    get_exposure_by_supplier,
    get_exposure_by_doc_type,
    get_high_value_risk_invoices,
    get_aging_buckets,
)

financial_risk_bp = Blueprint('financial_risk', __name__)


@financial_risk_bp.route('/financial-risk/summary', methods=['GET'])
def financial_risk_summary():
    return jsonify(get_financial_risk_summary())


@financial_risk_bp.route('/financial-risk/exposure-by-supplier', methods=['GET'])
def exposure_by_supplier():
    return jsonify(get_exposure_by_supplier())


@financial_risk_bp.route('/financial-risk/exposure-by-doc-type', methods=['GET'])
def exposure_by_doc_type():
    return jsonify(get_exposure_by_doc_type())


@financial_risk_bp.route('/financial-risk/high-value-invoices', methods=['GET'])
def high_value_invoices():
    return jsonify(get_high_value_risk_invoices())


@financial_risk_bp.route('/financial-risk/aging-buckets', methods=['GET'])
def aging_buckets():
    return jsonify(get_aging_buckets())
