"""
Monthly Analysis page - detailed month-by-month spending analysis.
"""

import streamlit as st
import plotly.graph_objects as go
from src.storage import (
    load_transactions, get_available_months, filter_by_month,
    get_month_comparison, get_monthly_trend
)
from src.dashboard import create_spending_by_category_pie, create_merchant_bar_chart
from src.insights import generate_monthly_insights


def show_monthly_analysis_page():
    """Display detailed monthly analysis with month-over-month comparison."""
    st.title("📅 Monthly Analysis")
    
    username = st.session_state.user["username"]
    df = load_transactions(username)
    
    if df.empty:
        st.info("📤 Upload bank statements to see monthly analysis.")
        return
    
    # Get available months
    available_months = get_available_months(df)
    
    if not available_months:
        st.warning("No monthly data available yet.")
        return
    
    # Month selector at top of page
    col1, col2 = st.columns([2, 1])
    
    with col1:
        month_options = {m['month_name']: m for m in available_months}
        selected_label = st.selectbox(
            "📆 Select Month to Analyze",
            options=list(month_options.keys()),
            key="monthly_analysis_selector"
        )
        selected = month_options[selected_label]
    
    with col2:
        st.markdown("###")  # Spacing
        generate_ai = st.button("🤖 Generate AI Analysis", type="primary", use_container_width=True)
    
    year, month = selected["year"], selected["month"]
    
    # Get comparison data
    comparison = get_month_comparison(df, year, month)
    month_df = filter_by_month(df, year, month)
    
    st.divider()
    
    # Summary metrics with comparison
    st.subheader(f"📊 {comparison['current_month']} Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_str = None
        if comparison["has_previous_data"] and comparison["changes"]["credit"]:
            delta_str = f"{comparison['changes']['credit']:+.1f}%"
        st.metric(
            "💰 Income",
            f"₹{comparison['current']['credit']:,.0f}",
            delta=delta_str
        )
    
    with col2:
        delta_str = None
        if comparison["has_previous_data"] and comparison["changes"]["debit"]:
            delta_str = f"{comparison['changes']['debit']:+.1f}%"
        st.metric(
            "💸 Spending",
            f"₹{comparison['current']['debit']:,.0f}",
            delta=delta_str,
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "💵 Net Savings",
            f"₹{comparison['current']['net']:,.0f}",
            delta=f"₹{comparison['changes']['net_diff']:+,.0f}" if comparison["has_previous_data"] else None
        )
    
    with col4:
        savings_rate = 0
        if comparison['current']['credit'] > 0:
            savings_rate = (comparison['current']['net'] / comparison['current']['credit']) * 100
        st.metric(
            "📈 Savings Rate",
            f"{savings_rate:.1f}%"
        )
    
    st.divider()
    
    # Month-over-month comparison section
    if comparison["has_previous_data"]:
        st.subheader(f"📈 Compared to {comparison['previous_month']}")
        
        # Category changes - sorted by absolute change
        cat_changes = comparison["category_changes"]
        sorted_cats = sorted(cat_changes.items(), key=lambda x: abs(x[1].get("change", 0)), reverse=True)
        
        # Show increases and decreases
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 🔺 Increased Spending")
            increases = [(cat, data) for cat, data in sorted_cats if data["change"] > 0]
            if increases:
                for cat, data in increases[:5]:
                    pct = data.get("change_pct")
                    pct_str = f" ({pct:+.0f}%)" if pct else ""
                    st.markdown(f"**{cat}**: ₹{data['current']:,.0f} (+₹{data['change']:,.0f}){pct_str}")
            else:
                st.success("No categories increased! 🎉")
        
        with col2:
            st.markdown("##### 🔻 Decreased Spending")
            decreases = [(cat, data) for cat, data in sorted_cats if data["change"] < 0]
            if decreases:
                for cat, data in decreases[:5]:
                    pct = data.get("change_pct")
                    pct_str = f" ({pct:.0f}%)" if pct else ""
                    st.markdown(f"**{cat}**: ₹{data['current']:,.0f} (-₹{abs(data['change']):,.0f}){pct_str}")
            else:
                st.info("No decreases this month")
    else:
        st.info(f"ℹ️ No data for {comparison['previous_month']} to compare against.")
    
    st.divider()
    
    # Charts for the month
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            create_spending_by_category_pie(month_df, "DEBIT"),
            use_container_width=True
        )
    
    with col2:
        st.plotly_chart(
            create_merchant_bar_chart(month_df),
            use_container_width=True
        )
    
    # Top merchants table
    st.subheader("🏪 Top Merchants This Month")
    if comparison["top_merchants"]:
        merchant_data = []
        for m in comparison["top_merchants"]:
            merchant_data.append({
                "Merchant": m["name"],
                "Total Spent": f"₹{m['amount']:,.0f}",
                "Transactions": m["count"],
                "Avg per Transaction": f"₹{m['amount']/m['count']:,.0f}"
            })
        st.dataframe(merchant_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # AI Insights section
    st.subheader("🤖 AI-Powered Monthly Insights")
    
    if generate_ai or f"monthly_insights_{year}_{month}" in st.session_state:
        if generate_ai:
            with st.spinner(f"Analyzing {selected['month_name']}..."):
                insights = generate_monthly_insights(
                    month_df,
                    year,
                    month,
                    st.session_state.user.get("monthly_income", 0),
                    st.session_state.user.get("display_name", "there"),
                    comparison
                )
                st.session_state[f"monthly_insights_{year}_{month}"] = insights
        
        if f"monthly_insights_{year}_{month}" in st.session_state:
            st.markdown(st.session_state[f"monthly_insights_{year}_{month}"])
    else:
        st.info("👆 Click 'Generate AI Analysis' for personalized insights about this month's spending.")
    
    st.divider()
    
    # Monthly trend chart (last 6 months)
    st.subheader("📊 Monthly Spending Trend")
    trend_data = get_monthly_trend(df, num_months=6)
    
    if trend_data:
        fig = go.Figure()
        
        months = [t["month"] for t in trend_data]
        credits = [t["credit"] for t in trend_data]
        debits = [t["debit"] for t in trend_data]
        nets = [t["net"] for t in trend_data]
        
        fig.add_trace(go.Bar(
            name="💰 Income",
            x=months,
            y=credits,
            marker=dict(
                color="#10B981",
                line=dict(color="white", width=2)
            ),
            text=[f"₹{v:,.0f}" for v in credits],
            textposition="outside",
            textfont=dict(size=9, color="#1F2937"),
            hovertemplate="<b>%{x}</b><br>💰 Income: ₹%{y:,.0f}<extra></extra>"
        ))
        
        fig.add_trace(go.Bar(
            name="💸 Spending",
            x=months,
            y=debits,
            marker=dict(
                color="#EF4444",
                line=dict(color="white", width=2)
            ),
            text=[f"₹{v:,.0f}" for v in debits],
            textposition="outside",
            textfont=dict(size=9, color="#1F2937"),
            hovertemplate="<b>%{x}</b><br>💸 Spending: ₹%{y:,.0f}<extra></extra>"
        ))
        
        fig.add_trace(go.Scatter(
            name="📈 Net Savings",
            x=months,
            y=nets,
            mode="lines+markers+text",
            line=dict(color="#06B6D4", width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(6, 182, 212, 0.15)",
            marker=dict(
                size=12,
                symbol="circle",
                line=dict(color="white", width=2),
                color="#06B6D4"
            ),
            text=[f"₹{v:,.0f}" for v in nets],
            textposition="top center",
            textfont=dict(size=10, color="#1F2937"),
            hovertemplate="<b>%{x}</b><br>📈 Net: ₹%{y:,.0f}<extra></extra>"
        ))
        
        fig.update_layout(
            barmode="group",
            title=dict(
                text="💹 Income vs Spending Trend (Last 6 Months)",
                font=dict(size=18, family="Arial Black, sans-serif", color="#1F2937"),
                x=0.5,
                xanchor="center"
            ),
            xaxis_title="Month",
            yaxis_title="Amount (₹)",
            height=420,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="#6B7280",
                borderwidth=1
            ),
            margin=dict(t=80, b=60, l=70, r=20),
            paper_bgcolor="#F3F4F6",
            plot_bgcolor="#FFFFFF",
            xaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(107, 114, 128, 0.1)"),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(107, 114, 128, 0.1)"),
            font=dict(family="Arial, sans-serif", size=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)
