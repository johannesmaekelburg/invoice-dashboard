from flask import Blueprint, jsonify
from functions.issue_patterns_service import (
    get_issue_summary,
    get_top_issue_categories,
    get_issues_by_section,
    get_issues_by_supplier,
    get_severity_breakdown,
)

issue_patterns_bp = Blueprint('issue_patterns', __name__)


@issue_patterns_bp.route('/issue-patterns/summary', methods=['GET'])
def issue_summary():
    return jsonify(get_issue_summary())


@issue_patterns_bp.route('/issue-patterns/top-categories', methods=['GET'])
def top_categories():
    return jsonify(get_top_issue_categories())


@issue_patterns_bp.route('/issue-patterns/by-section', methods=['GET'])
def by_section():
    return jsonify(get_issues_by_section())


@issue_patterns_bp.route('/issue-patterns/by-supplier', methods=['GET'])
def by_supplier():
    return jsonify(get_issues_by_supplier())


@issue_patterns_bp.route('/issue-patterns/severity-breakdown', methods=['GET'])
def severity_breakdown():
    return jsonify(get_severity_breakdown())
