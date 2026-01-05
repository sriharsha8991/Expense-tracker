"""
Insights page - displays AI-powered financial insights and recommendations.
"""

import streamlit as st
from src.storage import load_transactions, filter_transactions_by_date, get_date_range_filter
from src.analyzer import analyze_spending_patterns, detect_anomalies, calculate_savings_potential
from src.insights import generate_spending_insights, get_investment_suggestions


def show_insights_page():
    """Display AI-powered insights."""
    st.title("💡 AI Financial Insights")
    
    username = st.session_state.user["username"]
    df = load_transactions(username)
    
    if df.empty:
        st.info("Upload bank statements to get personalized insights.")
        return
    
    # Apply time filter
    time_range = st.session_state.get("time_range", "month")
    start_date, end_date = get_date_range_filter(time_range)
    filtered_df = filter_transactions_by_date(df, start_date, end_date)
    
    # Generate insights button
    if st.button("🔄 Generate Fresh Insights", type="primary"):
        with st.spinner("Analyzing your spending patterns..."):
            insights = generate_spending_insights(
                filtered_df,
                st.session_state.user.get("monthly_income", 0),
                st.session_state.user.get("display_name", "there")
            )
            st.session_state.last_insights = insights
    
    # Display insights
    if "last_insights" in st.session_state:
        st.markdown(st.session_state.last_insights)
    else:
        # Show basic analysis
        st.markdown("### 📈 Spending Patterns")
        
        patterns = analyze_spending_patterns(filtered_df)
        if patterns:
            for pattern in patterns[:5]:
                icon = "📈" if pattern.trend == "up" else "📉" if pattern.trend == "down" else "➡️"
                change_text = f"+{pattern.change_percent:.0f}%" if pattern.change_percent > 0 else f"{pattern.change_percent:.0f}%"
                st.markdown(f"{icon} **{pattern.category}**: ₹{pattern.current_amount:,.0f} ({change_text} vs average)")
    
    st.divider()
    
    # Savings potential
    st.markdown("### 💰 Savings Potential")
    
    savings = calculate_savings_potential(filtered_df, st.session_state.user.get("monthly_income", 0))
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Essential Spending", f"₹{savings['essential_spend']:,.0f}")
    with col2:
        st.metric("Discretionary Spending", f"₹{savings['discretionary_spend']:,.0f}")
    with col3:
        st.metric("Savings Rate", f"{savings['savings_rate']:.1f}%")
    
    # Potential savings suggestions
    if savings.get("potential_savings"):
        st.markdown("#### 💡 Where You Could Save")
        for saving in savings["potential_savings"]:
            with st.expander(f"**{saving['category']}** - Save ₹{saving['suggested_reduction']:,.0f}/month"):
                st.write(f"Current spend: ₹{saving['current_spend']:,.0f}")
                st.info(saving["tip"])
    
    st.divider()
    
    # Investment suggestions
    st.markdown("### 📊 Investment Suggestions")
    
    monthly_surplus = savings.get("total_income", 0) - savings.get("total_spend", 0)
    suggestions = get_investment_suggestions(savings["savings_rate"], monthly_surplus)
    
    for suggestion in suggestions:
        priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        st.markdown(f"{priority_color.get(suggestion['priority'], '⚪')} **{suggestion['type']}**: {suggestion['message']}")
    
    st.divider()
    
    # Anomalies
    st.markdown("### ⚠️ Unusual Transactions")
    
    anomalies = detect_anomalies(filtered_df)
    if anomalies:
        for anomaly in anomalies[:5]:
            severity_icon = {"high": "🔴", "medium": "🟠", "low": "🟡"}
            st.warning(f"""
            {severity_icon.get(anomaly.severity, '⚪')} **{anomaly.merchant}** - ₹{anomaly.amount:,.0f}
            
            {anomaly.reason}
            """)
    else:
        st.success("No unusual transactions detected. Your spending looks consistent! 👍")
