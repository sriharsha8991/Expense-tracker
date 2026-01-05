"""
Dashboard module for the Expense Tracker.
Contains Plotly chart components and visualization utilities.
"""

import plotly.express as px
import plotly.graph_objects as go
from plotly.subplots import make_subplots
import pandas as pd
from typing import Dict, Any, List
from datetime import datetime, timedelta


# Modern color palette for consistent styling
COLORS = {
    "primary": "#6366F1",      # Deep Indigo
    "success": "#10B981",      # Emerald Green (Credit)
    "danger": "#EF4444",       # Vibrant Red (Debit)
    "warning": "#F59E0B",      # Amber/Gold
    "info": "#06B6D4",         # Cyan
    "gray": "#6B7280",
    "dark": "#1F2937",
    "light": "#F3F4F6",
}

# Rich, gradient-friendly color palette for categories
CATEGORY_COLORS = {
    "SALARY": "#10B981",           # Emerald
    "EMI": "#EF4444",              # Red
    "RENT": "#F59E0B",             # Amber
    "UTILITIES": "#8B5CF6",        # Purple
    "FOOD": "#EC4899",             # Pink
    "GROCERIES": "#14B8A6",        # Teal
    "SHOPPING": "#F97316",         # Orange
    "TRANSPORT": "#6366F1",        # Indigo
    "INVESTMENT": "#22C55E",       # Green
    "ENTERTAINMENT": "#A855F7",    # Violet
    "MEDICAL": "#06B6D4",          # Cyan
    "TRANSFER": "#64748B",         # Slate
    "ATM": "#78716C",              # Stone
    "BANK_CHARGES": "#9CA3AF",     # Gray
    "INSURANCE": "#3B82F6",        # Blue
    "GIFTS": "#EC4899",            # Rose
    "TRAVEL": "#14B8A6",           # Teal
    "UNCATEGORIZED": "#D1D5DB",    # Light Gray
}


def create_spending_by_category_pie(df: pd.DataFrame, direction: str = "DEBIT") -> go.Figure:
    """
    Create a pie chart showing spending breakdown by category.
    
    Args:
        df: DataFrame with transactions
        direction: "DEBIT" for spending, "CREDIT" for income
    
    Returns:
        Plotly Figure
    """
    if df.empty:
        return _create_empty_chart("No transactions found")
    
    filtered = df[df["direction"] == direction]
    if filtered.empty:
        return _create_empty_chart(f"No {direction.lower()} transactions found")
    
    category_totals = filtered.groupby("category")["amount"].sum().reset_index()
    category_totals = category_totals.sort_values("amount", ascending=False)
    
    # Get colors for categories
    colors = [CATEGORY_COLORS.get(cat, "#D1D5DB") for cat in category_totals["category"]]
    
    fig = go.Figure(data=[go.Pie(
        labels=category_totals["category"],
        values=category_totals["amount"],
        hole=0.3,
        marker_colors=colors,
        marker_line=dict(color="#FFFFFF", width=2),
        textinfo="label+percent",
        textposition="outside",
        textfont=dict(size=11, family="Arial, sans-serif"),
        hovertemplate="<b>%{label}</b><br>₹%{value:,.2f}<br>%{percent}<extra></extra>",
        pull=[0.05 if i == 0 else 0 for i in range(len(category_totals))]
    )])
    
    title = "💰 Spending by Category" if direction == "DEBIT" else "💵 Income by Category"
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20, family="Arial Black, sans-serif", color=COLORS["dark"]),
            x=0.5,
            xanchor="center"
        ),
        showlegend=True,
        legend=dict(
            orientation="v",
            yanchor="middle",
            y=0.5,
            xanchor="left",
            x=1.02,
            font=dict(size=10)
        ),
        margin=dict(t=60, b=20, l=20, r=150),
        height=420,
        paper_bgcolor=COLORS["light"],
        plot_bgcolor=COLORS["light"],
        font=dict(family="Arial, sans-serif")
    )
    
    return fig


def create_spending_trend_line(df: pd.DataFrame) -> go.Figure:
    """
    Create a line chart showing daily spending/income trend.
    
    Args:
        df: DataFrame with transactions
    
    Returns:
        Plotly Figure
    """
    if df.empty:
        return _create_empty_chart("No transactions found")
    
    # Ensure date column is datetime
    df = df.copy()
    df["date"] = pd.to_datetime(df["transaction_date"]).dt.date
    
    # Group by date and direction
    daily = df.groupby(["date", "direction"])["amount"].sum().unstack(fill_value=0).reset_index()
    
    fig = go.Figure()
    
    if "DEBIT" in daily.columns:
        fig.add_trace(go.Scatter(
            x=daily["date"],
            y=daily["DEBIT"],
            mode="lines+markers",
            name="Spending",
            line=dict(color=COLORS["danger"], width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(239, 68, 68, 0.1)",
            marker=dict(size=8, symbol="circle", line=dict(color="white", width=2)),
            hovertemplate="<b>%{x}</b><br>💸 Spent: ₹%{y:,.2f}<extra></extra>"
        ))
    
    if "CREDIT" in daily.columns:
        fig.add_trace(go.Scatter(
            x=daily["date"],
            y=daily["CREDIT"],
            mode="lines+markers",
            name="Income",
            line=dict(color=COLORS["success"], width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(16, 185, 129, 0.1)",
            marker=dict(size=8, symbol="circle", line=dict(color="white", width=2)),
            hovertemplate="<b>%{x}</b><br>💰 Received: ₹%{y:,.2f}<extra></extra>"
        ))
    
    fig.update_layout(
        title=dict(
            text="📈 Daily Money Flow",
            font=dict(size=20, family="Arial Black, sans-serif", color=COLORS["dark"]),
            x=0.5,
            xanchor="center"
        ),
        xaxis_title="Date",
        yaxis_title="Amount (₹)",
        hovermode="x unified",
        legend=dict(
            orientation="h",
            yanchor="bottom",
            y=1.02,
            xanchor="right",
            x=1,
            bgcolor="rgba(255, 255, 255, 0.8)",
            bordercolor=COLORS["gray"],
            borderwidth=1
        ),
        margin=dict(t=80, b=60, l=70, r=20),
        height=380,
        paper_bgcolor=COLORS["light"],
        plot_bgcolor="#FFFFFF",
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(107, 114, 128, 0.1)"),
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(107, 114, 128, 0.1)"),
        font=dict(family="Arial, sans-serif", size=10)
    )
    
    return fig


def create_category_bar_chart(df: pd.DataFrame, direction: str = "DEBIT", top_n: int = 10) -> go.Figure:
    """
    Create a horizontal bar chart showing top categories.
    
    Args:
        df: DataFrame with transactions
        direction: "DEBIT" or "CREDIT"
        top_n: Number of top categories to show
    
    Returns:
        Plotly Figure
    """
    if df.empty:
        return _create_empty_chart("No transactions found")
    
    filtered = df[df["direction"] == direction]
    if filtered.empty:
        return _create_empty_chart(f"No {direction.lower()} transactions found")
    
    category_totals = filtered.groupby("category")["amount"].sum().sort_values(ascending=True).tail(top_n)
    
    colors = [CATEGORY_COLORS.get(cat, "#D1D5DB") for cat in category_totals.index]
    
    fig = go.Figure(data=[go.Bar(
        x=category_totals.values,
        y=category_totals.index,
        orientation="h",
        marker=dict(
            color=colors,
            line=dict(color="white", width=2)
        ),
        text=[f"₹{v:,.0f}" for v in category_totals.values],
        textposition="outside",
        textfont=dict(size=10, family="Arial, sans-serif", color=COLORS["dark"]),
        hovertemplate="<b>%{y}</b><br>₹%{x:,.2f}<extra></extra>"
    )])
    
    title = "🛍️ Top Spending Categories" if direction == "DEBIT" else "💵 Top Income Sources"
    fig.update_layout(
        title=dict(
            text=title,
            font=dict(size=20, family="Arial Black, sans-serif", color=COLORS["dark"]),
            x=0.5,
            xanchor="center"
        ),
        xaxis_title="Amount (₹)",
        yaxis_title="",
        margin=dict(t=60, b=60, l=130, r=80),
        height=420,
        paper_bgcolor=COLORS["light"],
        plot_bgcolor="#FFFFFF",
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(107, 114, 128, 0.1)"),
        yaxis=dict(showgrid=False),
        font=dict(family="Arial, sans-serif", size=10)
    )
    
    return fig


def create_merchant_bar_chart(df: pd.DataFrame, top_n: int = 10) -> go.Figure:
    """
    Create a bar chart showing top merchants by spending.
    
    Args:
        df: DataFrame with transactions
        top_n: Number of top merchants to show
    
    Returns:
        Plotly Figure
    """
    if df.empty:
        return _create_empty_chart("No transactions found")
    
    # Filter debits and valid merchants
    debits = df[(df["direction"] == "DEBIT") & (df["merchant_name"].notna()) & (df["merchant_name"] != "UNKNOWN")]
    if debits.empty:
        return _create_empty_chart("No merchant data available")
    
    merchant_totals = debits.groupby("merchant_name")["amount"].sum().sort_values(ascending=True).tail(top_n)
    
    fig = go.Figure(data=[go.Bar(
        x=merchant_totals.values,
        y=merchant_totals.index,
        orientation="h",
        marker=dict(
            color=COLORS["primary"],
            line=dict(color="white", width=2)
        ),
        text=[f"₹{v:,.0f}" for v in merchant_totals.values],
        textposition="outside",
        textfont=dict(size=10, family="Arial, sans-serif", color=COLORS["dark"]),
        hovertemplate="<b>%{y}</b><br>₹%{x:,.2f}<extra></extra>"
    )])
    
    fig.update_layout(
        title=dict(
            text="🏪 Top Merchants by Spending",
            font=dict(size=20, family="Arial Black, sans-serif", color=COLORS["dark"]),
            x=0.5,
            xanchor="center"
        ),
        xaxis_title="Amount (₹)",
        yaxis_title="",
        margin=dict(t=60, b=60, l=160, r=80),
        height=420,
        paper_bgcolor=COLORS["light"],
        plot_bgcolor="#FFFFFF",
        xaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(107, 114, 128, 0.1)"),
        yaxis=dict(showgrid=False),
        font=dict(family="Arial, sans-serif", size=10)
    )
    
    return fig


def create_credit_debit_comparison(df: pd.DataFrame) -> go.Figure:
    """
    Create a comparison chart showing credit vs debit totals.
    
    Args:
        df: DataFrame with transactions
    
    Returns:
        Plotly Figure
    """
    if df.empty:
        return _create_empty_chart("No transactions found")
    
    total_credit = df[df["direction"] == "CREDIT"]["amount"].sum()
    total_debit = df[df["direction"] == "DEBIT"]["amount"].sum()
    
    fig = go.Figure(data=[
        go.Bar(
            x=["Income", "Spending"],
            y=[total_credit, total_debit],
            marker=dict(
                color=[COLORS["success"], COLORS["danger"]],
                line=dict(color="white", width=2)
            ),
            text=[f"₹{total_credit:,.0f}", f"₹{total_debit:,.0f}"],
            textposition="outside",
            textfont=dict(size=12, family="Arial, sans-serif", color=COLORS["dark"]),
            hovertemplate="<b>%{x}</b><br>₹%{y:,.2f}<extra></extra>"
        )
    ])
    
    # Add net flow annotation
    net_flow = total_credit - total_debit
    net_color = COLORS["success"] if net_flow >= 0 else COLORS["danger"]
    net_sign = "+" if net_flow >= 0 else ""
    
    fig.update_layout(
        title=dict(
            text="💰 Income vs Spending",
            font=dict(size=20, family="Arial Black, sans-serif", color=COLORS["dark"]),
            x=0.5,
            xanchor="center"
        ),
        yaxis_title="Amount (₹)",
        annotations=[
            dict(
                x=0.5,
                y=1.15,
                xref="paper",
                yref="paper",
                text=f"<b>Net Savings: {net_sign}₹{abs(net_flow):,.0f}</b>",
                showarrow=False,
                font=dict(size=14, color=net_color, family="Arial Black, sans-serif")
            )
        ],
        margin=dict(t=100, b=60, l=70, r=20),
        height=380,
        paper_bgcolor=COLORS["light"],
        plot_bgcolor="#FFFFFF",
        yaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(107, 114, 128, 0.1)"),
        font=dict(family="Arial, sans-serif", size=10)
    )
    
    return fig


def create_weekly_heatmap(df: pd.DataFrame) -> go.Figure:
    """
    Create a heatmap showing spending by day of week.
    
    Args:
        df: DataFrame with transactions
    
    Returns:
        Plotly Figure
    """
    if df.empty:
        return _create_empty_chart("No transactions found")
    
    df = df.copy()
    df["date"] = pd.to_datetime(df["transaction_date"])
    df["day_of_week"] = df["date"].dt.day_name()
    df["week"] = df["date"].dt.isocalendar().week
    
    debits = df[df["direction"] == "DEBIT"]
    if debits.empty:
        return _create_empty_chart("No spending data")
    
    # Pivot for heatmap
    pivot = debits.groupby(["week", "day_of_week"])["amount"].sum().unstack(fill_value=0)
    
    # Reorder days
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    pivot = pivot.reindex(columns=[d for d in day_order if d in pivot.columns])
    
    fig = go.Figure(data=go.Heatmap(
        z=pivot.values,
        x=pivot.columns,
        y=[f"Week {w}" for w in pivot.index],
        colorscale=[
            [0, "#F3F4F6"],
            [0.3, "#FEE2E2"],
            [0.6, "#FECACA"],
            [1, "#DC2626"]
        ],
        text=[[f"₹{v:,.0f}" for v in row] for row in pivot.values],
        texttemplate="%{text}",
        textfont=dict(size=9, color=COLORS["dark"]),
        hovertemplate="<b>%{x}</b><br>%{y}<br>₹%{z:,.0f}<extra></extra>",
        colorbar=dict(title="Amount (₹)", thickness=20, len=0.7)
    ))
    
    fig.update_layout(
        title=dict(
            text="🔥 Spending Heatmap by Day",
            font=dict(size=20, family="Arial Black, sans-serif", color=COLORS["dark"]),
            x=0.5,
            xanchor="center"
        ),
        xaxis_title="Day of Week",
        yaxis_title="",
        margin=dict(t=60, b=60, l=80, r=100),
        height=320,
        paper_bgcolor=COLORS["light"],
        plot_bgcolor="white",
        font=dict(family="Arial, sans-serif", size=10)
    )
    
    return fig


def _create_empty_chart(message: str) -> go.Figure:
    """Create an empty chart with a message."""
    fig = go.Figure()
    fig.add_annotation(
        text=f"📊 {message}",
        xref="paper",
        yref="paper",
        x=0.5,
        y=0.5,
        showarrow=False,
        font=dict(size=16, color=COLORS["gray"], family="Arial, sans-serif")
    )
    fig.update_layout(
        xaxis=dict(visible=False),
        yaxis=dict(visible=False),
        height=300,
        paper_bgcolor=COLORS["light"],
        plot_bgcolor=COLORS["light"]
    )
    return fig


# --- Metric Cards ---

def format_currency(amount: float) -> str:
    """Format amount as Indian currency."""
    if amount >= 10000000:  # 1 Crore
        return f"₹{amount/10000000:.2f} Cr"
    elif amount >= 100000:  # 1 Lakh
        return f"₹{amount/100000:.2f} L"
    elif amount >= 1000:
        return f"₹{amount/1000:.1f}K"
    else:
        return f"₹{amount:,.0f}"


def get_metric_cards_data(df: pd.DataFrame, monthly_income: float = 0) -> List[Dict]:
    """
    Get data for metric cards display.
    
    Args:
        df: DataFrame with transactions
        monthly_income: User's monthly income for calculations
    
    Returns:
        List of dicts with metric data
    """
    if df.empty:
        return [
            {"label": "Total Transactions", "value": "0", "delta": None, "color": "gray"},
            {"label": "Total Income", "value": "₹0", "delta": None, "color": "green"},
            {"label": "Total Spending", "value": "₹0", "delta": None, "color": "red"},
            {"label": "Net Savings", "value": "₹0", "delta": None, "color": "blue"},
        ]
    
    total_credit = df[df["direction"] == "CREDIT"]["amount"].sum()
    total_debit = df[df["direction"] == "DEBIT"]["amount"].sum()
    net_flow = total_credit - total_debit
    
    # Calculate savings rate if income available
    savings_rate = None
    if monthly_income > 0:
        savings_rate = f"{(net_flow / monthly_income * 100):.1f}%"
    
    return [
        {
            "label": "Total Transactions",
            "value": str(len(df)),
            "delta": None,
            "color": "primary"
        },
        {
            "label": "Total Income",
            "value": format_currency(total_credit),
            "delta": None,
            "color": "success"
        },
        {
            "label": "Total Spending",
            "value": format_currency(total_debit),
            "delta": None,
            "color": "danger"
        },
        {
            "label": "Net Savings",
            "value": format_currency(abs(net_flow)),
            "delta": savings_rate,
            "color": "success" if net_flow >= 0 else "danger",
            "prefix": "+" if net_flow >= 0 else "-"
        },
    ]
