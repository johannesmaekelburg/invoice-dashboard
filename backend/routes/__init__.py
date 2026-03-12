from flask import Blueprint

# Import all blueprints
from .shapes_overview_routes import shapes_overview_bp
from .landing_routes import landing_bp
from .homepage_routes import homepage_bp
from .shape_view_routes import shape_view_bp
from .invoice_routes import invoice_bp
from .financial_risk_routes import financial_risk_bp
from .issue_patterns_routes import issue_patterns_bp

# List of all blueprints to be registered in the app
blueprints = [
    shapes_overview_bp,
    landing_bp,
    homepage_bp,
    shape_view_bp,
    invoice_bp,
    financial_risk_bp,
    issue_patterns_bp,
]
