"""
Pages module - contains all page components for the Streamlit app.
"""

from .auth_page import show_login_page
from .dashboard_page import show_dashboard_page
from .monthly_analysis_page import show_monthly_analysis_page
from .upload_page import show_upload_page
from .insights_page import show_insights_page
from .transactions_page import show_transactions_page
from .settings_page import show_settings_page

__all__ = [
    "show_login_page",
    "show_dashboard_page",
    "show_monthly_analysis_page",
    "show_upload_page",
    "show_insights_page",
    "show_transactions_page",
    "show_settings_page",
]
