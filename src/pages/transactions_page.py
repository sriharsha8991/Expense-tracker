"""
Transactions page - displays searchable transaction list with filters.
"""

import streamlit as st
import pandas as pd
from datetime import datetime
from src.storage import (
    load_transactions, filter_transactions_by_date, get_date_range_filter,
    get_available_months, filter_by_month
)


def show_transactions_page():
    """Display all transactions with filters."""
    st.title("📋 All Transactions")
    
    username = st.session_state.user["username"]
    df = load_transactions(username)
    
    if df.empty:
        st.info("No transactions yet. Upload a bank statement to get started.")
        return
    
    # Get available months
    available_months = get_available_months(df)
    
    # Filter mode selector
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        filter_mode = st.radio(
            "Filter by",
            options=["all", "time_period", "specific_month"],
            format_func=lambda x: {
                "all": "Show All",
                "time_period": "Time Period (7d, 30d, etc.)",
                "specific_month": "Specific Month (Oct, Nov, etc.)"
            }[x],
            horizontal=True,
            key="transactions_filter_mode"
        )
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        categories = ["All"] + list(df["category"].unique())
        selected_category = st.selectbox("📁 Category", categories)
    
    with col2:
        directions = ["All", "💰 Income", "💸 Spending"]
        selected_direction = st.selectbox("Type", directions)
    
    with col3:
        search = st.text_input("🔍 Search", placeholder="Description or merchant...")
    
    with col4:
        min_amount = st.number_input("Min Amount (₹)", value=0, step=100)
    
    # Apply filters
    filtered = df.copy()
    
    if selected_category != "All":
        filtered = filtered[filtered["category"] == selected_category]
    
    if selected_direction != "All":
        direction_map = {"💰 Income": "CREDIT", "💸 Spending": "DEBIT"}
        selected_direction_code = direction_map.get(selected_direction, selected_direction)
        filtered = filtered[filtered["direction"] == selected_direction_code]
    
    if search:
        filtered = filtered[filtered["description"].str.contains(search, case=False, na=False)]
    
    if min_amount > 0:
        filtered = filtered[filtered["amount"] >= min_amount]
    
    # Apply time filter based on mode
    if filter_mode == "time_period":
        time_range = st.session_state.get("time_range", "month")
        start_date, end_date = get_date_range_filter(time_range)
        filtered = filter_transactions_by_date(filtered, start_date, end_date)
        period_info = f"({time_range.replace('6months', 'Last 6 months').replace('month', 'Last 30 days').replace('2weeks', 'Last 2 weeks').replace('week', 'Last 7 days')})"
    elif filter_mode == "specific_month":
        if available_months:
            month_options = {m['month_name']: m for m in available_months}
            selected_month_label = st.selectbox(
                "📆 Select Month",
                options=list(month_options.keys()),
                key="transactions_month_selector"
            )
            selected_month = month_options[selected_month_label]
            filtered = filter_by_month(filtered, selected_month["year"], selected_month["month"])
            period_info = f"({selected_month['month_name']})"
        else:
            period_info = ""
    else:
        period_info = "(All transactions)"
    
    # Display summary with period info
    st.markdown(f"### Showing **{len(filtered)}** transactions {period_info}")
    
    # Display transactions
    if not filtered.empty:
        # Sort by date descending (newest first)
        filtered = filtered.sort_values("transaction_date", ascending=False)
        
        # Format for display
        display_df = filtered[["transaction_date", "description", "amount", "direction", "category", "merchant_name"]].copy()
        display_df["transaction_date"] = pd.to_datetime(display_df["transaction_date"]).dt.strftime("%Y-%m-%d")
        
        # Color code by direction
        display_df["Type"] = display_df["direction"].apply(lambda x: "💰 Credit" if x == "CREDIT" else "💸 Debit")
        display_df["Amount (₹)"] = display_df["amount"].apply(lambda x: f"₹{x:,.2f}")
        
        display_df = display_df.rename(columns={
            "transaction_date": "Date",
            "description": "Description",
            "category": "Category",
            "merchant_name": "Merchant"
        })
        
        display_df = display_df[["Date", "Description", "Amount (₹)", "Type", "Category", "Merchant"]]
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=500,
            hide_index=True
        )
        
        # Statistics
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        
        total_debit = filtered[filtered["direction"] == "DEBIT"]["amount"].sum()
        total_credit = filtered[filtered["direction"] == "CREDIT"]["amount"].sum()
        net = total_credit - total_debit
        avg_transaction = filtered["amount"].mean()
        
        with col1:
            st.metric("💸 Total Spending", f"₹{total_debit:,.0f}")
        
        with col2:
            st.metric("💰 Total Income", f"₹{total_credit:,.0f}")
        
        with col3:
            st.metric("📈 Net", f"₹{net:,.0f}", delta=f"avg: ₹{avg_transaction:,.0f}")
        
        with col4:
            transaction_count = len(filtered)
            st.metric("📊 Count", transaction_count, delta=f"avg: ₹{avg_transaction:,.0f}")
        
        # Export option
        st.divider()
        csv = filtered.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            file_name=f"transactions_{username}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning(f"No transactions found matching your filters {period_info}")
