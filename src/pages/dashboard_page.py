"""
Dashboard page - displays financial overview and charts.
"""

import streamlit as st
from src.storage import (
    load_transactions, filter_transactions_by_date, get_date_range_filter,
    filter_by_month
)
from src.dashboard import (
    create_spending_by_category_pie, create_spending_trend_line,
    create_category_bar_chart, create_merchant_bar_chart,
    create_credit_debit_comparison, get_metric_cards_data
)


def show_dashboard_page():
    """Display the main dashboard."""
    st.title("📊 Financial Dashboard")
    
    # Load transactions
    username = st.session_state.user["username"]
    df = load_transactions(username)
    
    if df.empty:
        st.info("👋 Welcome! Upload your first bank statement to get started.")
        if st.button("📤 Upload Statement"):
            st.session_state.current_page = "upload"
            st.rerun()
        return
    
    # Apply time filter based on mode
    filter_mode = st.session_state.get("filter_mode", "relative")
    selected_month = st.session_state.get("selected_month_data")
    
    if filter_mode == "specific_month" and selected_month:
        # Filter by specific month
        filtered_df = filter_by_month(df, selected_month["year"], selected_month["month"])
        period_label = selected_month["month_name"]
    else:
        # Relative time range
        time_range = st.session_state.get("time_range", "month")
        start_date, end_date = get_date_range_filter(time_range)
        filtered_df = filter_transactions_by_date(df, start_date, end_date)
        period_label = {
            "week": "Last 7 days",
            "2weeks": "Last 2 weeks",
            "month": "Last 30 days",
            "6months": "Last 6 months"
        }.get(time_range, "Selected Period")
    
    st.caption(f"📅 Showing data for: **{period_label}**")
    
    if filtered_df.empty:
        st.warning(f"No transactions found for {period_label}.")
        return
    
    # Metric cards
    metrics = get_metric_cards_data(filtered_df, st.session_state.user.get("monthly_income", 0))
    
    cols = st.columns(4)
    for i, metric in enumerate(metrics):
        with cols[i]:
            prefix = metric.get("prefix", "")
            st.metric(
                label=metric["label"],
                value=f"{prefix}{metric['value']}",
                delta=metric.get("delta")
            )
    
    st.divider()
    
    # Charts row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            create_spending_by_category_pie(filtered_df, "DEBIT"),
            use_container_width=True
        )
    
    with col2:
        st.plotly_chart(
            create_credit_debit_comparison(filtered_df),
            use_container_width=True
        )
    
    # Charts row 2
    st.plotly_chart(
        create_spending_trend_line(filtered_df),
        use_container_width=True
    )
    
    # Charts row 3
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            create_category_bar_chart(filtered_df, "DEBIT"),
            use_container_width=True
        )
    
    with col2:
        st.plotly_chart(
            create_merchant_bar_chart(filtered_df),
            use_container_width=True
        )
