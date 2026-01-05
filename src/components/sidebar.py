"""
Sidebar component with navigation and filters.
"""

import streamlit as st
from src.storage import load_transactions, get_available_months


def show_sidebar():
    """Display the sidebar navigation."""
    with st.sidebar:
        st.title(f"👋 Hello, {st.session_state.user['display_name']}!")
        
        st.divider()
        
        # Navigation
        pages = {
            "📊 Dashboard": "dashboard",
            "📅 Monthly Analysis": "monthly",
            "📤 Upload Statement": "upload",
            "💡 AI Insights": "insights",
            "📋 Transactions": "transactions",
            "⚙️ Settings": "settings"
        }
        
        for label, page in pages.items():
            if st.button(label, use_container_width=True, 
                        type="primary" if st.session_state.current_page == page else "secondary"):
                st.session_state.current_page = page
                st.rerun()
        
        st.divider()
        
        # Time Period Selection
        st.markdown("### 📅 Time Period")
        
        # Load user transactions to get available months
        username = st.session_state.user["username"]
        df = load_transactions(username)
        available_months = get_available_months(df) if not df.empty else []
        
        # Filter mode toggle
        filter_mode = st.radio(
            "Select by",
            options=["relative", "specific_month"],
            format_func=lambda x: "Relative Period" if x == "relative" else "Specific Month",
            horizontal=True,
            key="filter_mode"
        )
        
        if filter_mode == "relative":
            time_range = st.selectbox(
                "Period",
                options=["week", "2weeks", "month", "6months"],
                format_func=lambda x: {
                    "week": "Last 7 days",
                    "2weeks": "Last 2 weeks",
                    "month": "Last 30 days",
                    "6months": "Last 6 months"
                }[x],
                key="time_range"
            )
            st.session_state.selected_month_data = None
        else:
            if available_months:
                # Month selector
                month_options = {f"{m['month_name']} ({m['transaction_count']} txns)": m for m in available_months}
                selected_label = st.selectbox(
                    "Select Month",
                    options=list(month_options.keys()),
                    key="month_selector"
                )
                st.session_state.selected_month_data = month_options[selected_label]
            else:
                st.info("📤 Upload statements to see months")
                st.session_state.selected_month_data = None
        
        st.divider()
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()
