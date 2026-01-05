"""
Smart Expense Tracker - Streamlit App (Refactored)
A personal money manager with AI-powered insights.
"""

import streamlit as st

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Smart Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import page modules
from src.pages.auth_page import show_login_page
from src.pages.dashboard_page import show_dashboard_page
from src.pages.monthly_analysis_page import show_monthly_analysis_page
from src.pages.upload_page import show_upload_page
from src.pages.insights_page import show_insights_page
from src.pages.transactions_page import show_transactions_page
from src.pages.settings_page import show_settings_page
from src.components.sidebar import show_sidebar


# --- Session State Initialization ---
def init_session_state():
    """Initialize session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"


init_session_state()


# --- Custom CSS ---
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        text-align: center;
    }
    .stMetric > div {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e2e8f0;
    }
    .success-box {
        background-color: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 1rem;
        border-radius: 0.25rem;
    }
    .warning-box {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 0.25rem;
    }
    .info-box {
        background-color: #dbeafe;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


# --- Main App ---
def main():
    """Main application entry point with routing."""
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_sidebar()
        
        # Route to current page
        page = st.session_state.current_page
        
        if page == "dashboard":
            show_dashboard_page()
        elif page == "monthly":
            show_monthly_analysis_page()
        elif page == "upload":
            show_upload_page()
        elif page == "insights":
            show_insights_page()
        elif page == "transactions":
            show_transactions_page()
        elif page == "settings":
            show_settings_page()
        else:
            st.error(f"Unknown page: {page}")


if __name__ == "__main__":
    main()
