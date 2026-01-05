"""
AI Insights module for the Expense Tracker.
Uses Gemini to generate personalized financial recommendations.
"""

import json
import google.generativeai as genai
from typing import Dict, Any, List, Optional
from src.models import MODEL_NAME
from src.analyzer import (
    analyze_spending_patterns,
    detect_anomalies,
    calculate_savings_potential,
    get_monthly_comparison
)
import pandas as pd


# Enhanced System instruction for precise financial analysis
ADVISOR_SYSTEM_INSTRUCTION = """
You are a precise Personal Finance Analyst AI specializing in Indian household budgets.
Your analysis must be DATA-DRIVEN with specific numbers and actionable recommendations.

## CRITICAL RULES:
1. **BE SPECIFIC**: Always cite exact amounts (e.g., "₹4,523 on Zomato across 12 orders" NOT "high food spending")
2. **NAME MERCHANTS**: Use actual merchant names from the data (e.g., "Swiggy", "Amazon", not just "food apps")
3. **CALCULATE SAVINGS**: Show math (e.g., "Cutting 4 Zomato orders × ₹350 avg = ₹1,400/month saved")
4. **COMPARE PERIODS**: Reference month-over-month changes when available
5. **NO GENERIC ADVICE**: Never say "spend less" or "save more" without specific amounts

## INDIAN BUDGET BENCHMARKS (as % of take-home income):
- Rent/Housing: 25-30% (EMI or rent)
- Food (groceries + dining): 15-20%
- Transport: 5-10%
- Utilities: 5%
- EMIs (non-housing): Should not exceed 20%
- Savings Target: 20%+ is healthy
- Discretionary: 10-15%

## RESPONSE STRUCTURE (FOLLOW EXACTLY):

### 📊 {Month} Financial Snapshot
[2-3 sentences: total income, total spend, net savings, savings rate. Compare to last month if data available.]

### 🔍 Key Findings

**1. Biggest Spending Area**
[Category name, exact amount, % of total spend, specific merchant breakdown]

**2. Month-over-Month Change**
[What increased/decreased most, by how much in ₹ and %, name specific merchants]

**3. Spending Pattern**
[Observation about frequency, timing, or habit - e.g., "8 late-night Swiggy orders (avg ₹420)"]

### ✅ This Week's Action Plan

1. **[Specific Action]** → Save ₹X/month
   [One-line explanation with merchant name]

2. **[Specific Action]** → Save ₹X/month
   [One-line explanation]

3. **[Specific Action]** → Save ₹X/month
   [One-line explanation]

**Total Potential Monthly Savings: ₹X**

### 💪 What's Working Well
[ONE specific positive observation with numbers - e.g., "Transport spending down 23% (₹1,200) vs last month"]

## SPECIAL CONSIDERATIONS:
- Festival months (Oct-Nov Diwali, Mar Holi): Higher shopping is expected
- Salary credit dates: Usually 1st or last week
- EMIs are fixed commitments - don't suggest reducing them
- UPI transfers to family may be recurring obligations
"""


def _create_advisor_model():
    """Create Gemini model for financial advice."""
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=ADVISOR_SYSTEM_INSTRUCTION,
        generation_config=genai.GenerationConfig(
            temperature=0.4,  # Lower temperature for more precise analysis
            max_output_tokens=1500
        )
    )


def generate_spending_insights(
    df: pd.DataFrame,
    monthly_income: float = 0,
    user_name: str = "there"
) -> str:
    """
    Generate AI-powered spending insights.
    
    Args:
        df: DataFrame with transactions
        monthly_income: User's monthly income
        user_name: User's display name
    
    Returns:
        Markdown-formatted insights string
    """
    if df.empty:
        return "📊 **No transaction data available yet.**\n\nUpload a bank statement to get personalized insights!"
    
    # Gather analysis data
    patterns = analyze_spending_patterns(df)
    anomalies = detect_anomalies(df)
    savings = calculate_savings_potential(df, monthly_income)
    monthly = get_monthly_comparison(df)
    
    # Build context for AI
    context = _build_analysis_context(df, patterns, anomalies, savings, monthly, monthly_income)
    
    # Generate insights with Gemini
    try:
        model = _create_advisor_model()
        
        prompt = f"""
        Analyze this spending data for {user_name} and provide personalized advice:
        
        {context}
        
        Remember to:
        - Be specific with amounts in ₹
        - Focus on the top 3 most impactful changes
        - Be encouraging about positive aspects
        - Keep the total response under 400 words
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        # Fallback to rule-based insights
        return _generate_fallback_insights(df, patterns, savings, user_name)


def _build_analysis_context(
    df: pd.DataFrame,
    patterns: list,
    anomalies: list,
    savings: Dict,
    monthly: list,
    monthly_income: float
) -> str:
    """Build context string for AI analysis."""
    
    # Basic stats
    total_credit = df[df["direction"] == "CREDIT"]["amount"].sum()
    total_debit = df[df["direction"] == "DEBIT"]["amount"].sum()
    transaction_count = len(df)
    
    # Category breakdown
    category_spend = df[df["direction"] == "DEBIT"].groupby("category")["amount"].sum().to_dict()
    category_str = "\n".join([f"  - {k}: ₹{v:,.0f}" for k, v in sorted(category_spend.items(), key=lambda x: -x[1])[:8]])
    
    # Top merchants
    merchants = df[df["direction"] == "DEBIT"].groupby("merchant_name")["amount"].sum().sort_values(ascending=False).head(5)
    merchant_str = "\n".join([f"  - {k}: ₹{v:,.0f}" for k, v in merchants.items() if k != "UNKNOWN"])
    
    # Pattern insights
    pattern_str = ""
    for p in patterns[:5]:
        if p.trend == "up":
            pattern_str += f"  - {p.category}: ₹{p.current_amount:,.0f} (↑{p.change_percent:.0f}% vs usual)\n"
        elif p.trend == "down":
            pattern_str += f"  - {p.category}: ₹{p.current_amount:,.0f} (↓{abs(p.change_percent):.0f}% vs usual)\n"
    
    # Anomalies
    anomaly_str = ""
    for a in anomalies[:3]:
        anomaly_str += f"  - {a.merchant} on {a.transaction_date}: ₹{a.amount:,.0f} ({a.reason})\n"
    
    # Detailed merchant analysis with transaction counts
    merchant_details = df[df["direction"] == "DEBIT"].groupby("merchant_name").agg({
        "amount": ["sum", "count", "mean"]
    }).round(2)
    merchant_details.columns = ["total", "count", "avg"]
    merchant_details = merchant_details.sort_values("total", ascending=False).head(10)
    
    merchant_detail_str = ""
    for name, row in merchant_details.iterrows():
        if name and name != "UNKNOWN":
            merchant_detail_str += f"  - {name}: ₹{row['total']:,.0f} ({int(row['count'])} transactions, avg ₹{row['avg']:,.0f})\n"
    
    # Category with transaction counts
    category_details = df[df["direction"] == "DEBIT"].groupby("category").agg({
        "amount": ["sum", "count"]
    }).round(2)
    category_details.columns = ["total", "count"]
    category_details = category_details.sort_values("total", ascending=False)
    category_details["pct"] = (category_details["total"] / category_details["total"].sum() * 100).round(1)
    
    category_detail_str = ""
    for cat, row in category_details.iterrows():
        category_detail_str += f"  - {cat}: ₹{row['total']:,.0f} ({row['pct']}% of spend, {int(row['count'])} transactions)\n"
    
    # Date range info
    date_min = df['transaction_date'].min()
    date_max = df['transaction_date'].max()
    
    # Get month name if single month
    month_name = ""
    if hasattr(date_min, 'strftime'):
        month_name = date_min.strftime("%B %Y")
    
    context = f"""
## FINANCIAL SNAPSHOT FOR {month_name.upper() if month_name else 'SELECTED PERIOD'}
- Analysis Period: {date_min} to {date_max}
- Total Transactions: {transaction_count}
- Total Income (Credits): ₹{total_credit:,.0f}
- Total Spending (Debits): ₹{total_debit:,.0f}
- Net Savings: ₹{total_credit - total_debit:,.0f}
- Savings Rate: {savings.get('savings_rate', 0):.1f}%
- User's Stated Monthly Income: ₹{monthly_income:,.0f}

## SPENDING BY CATEGORY (with % of total)
{category_detail_str}

## TOP 10 MERCHANTS (with frequency)
{merchant_detail_str}

## SPENDING TRENDS (current vs historical average)
{pattern_str if pattern_str else "  - Not enough historical data for comparison"}

## UNUSUAL/LARGE TRANSACTIONS
{anomaly_str if anomaly_str else "  - No unusual transactions detected"}

## SPENDING CLASSIFICATION
- Essential (EMI, Rent, Utilities, Medical, Groceries, Transport): ₹{savings.get('essential_spend', 0):,.0f}
- Discretionary (Food delivery, Shopping, Entertainment): ₹{savings.get('discretionary_spend', 0):,.0f}
- Discretionary as % of total spend: {(savings.get('discretionary_spend', 0) / max(total_debit, 1) * 100):.1f}%
"""
    return context


def _generate_fallback_insights(
    df: pd.DataFrame,
    patterns: list,
    savings: Dict,
    user_name: str
) -> str:
    """Generate rule-based insights when AI is unavailable."""
    
    total_credit = df[df["direction"] == "CREDIT"]["amount"].sum()
    total_debit = df[df["direction"] == "DEBIT"]["amount"].sum()
    net = total_credit - total_debit
    
    insights = f"## 📊 Financial Summary for {user_name}\n\n"
    
    # Summary
    if net >= 0:
        insights += f"✅ **Good news!** You saved ₹{net:,.0f} this period.\n\n"
    else:
        insights += f"⚠️ **Heads up:** You spent ₹{abs(net):,.0f} more than you earned.\n\n"
    
    # Key patterns
    insights += "### 📈 Key Observations\n\n"
    
    increasing = [p for p in patterns if p.trend == "up" and p.change_percent > 30]
    if increasing:
        for p in increasing[:2]:
            insights += f"- **{p.category}** spending increased by {p.change_percent:.0f}% (₹{p.current_amount:,.0f})\n"
    
    # Top category
    top_cat = df[df["direction"] == "DEBIT"].groupby("category")["amount"].sum().idxmax()
    top_amount = df[df["direction"] == "DEBIT"].groupby("category")["amount"].sum().max()
    insights += f"- Highest spend category: **{top_cat}** at ₹{top_amount:,.0f}\n\n"
    
    # Recommendations
    insights += "### 💡 Recommendations\n\n"
    
    for saving in savings.get("potential_savings", [])[:3]:
        insights += f"- Consider reducing **{saving['category']}** by ₹{saving['suggested_reduction']:,.0f}/month\n"
    
    if not savings.get("potential_savings"):
        insights += "- Keep tracking your expenses consistently\n"
        insights += "- Set specific savings goals for motivation\n"
    
    return insights


def generate_quick_tip(category: str, amount: float) -> str:
    """Generate a quick saving tip for a category."""
    tips = {
        "FOOD": f"💡 Tip: At ₹{amount:,.0f} on food, try cooking 2 more meals at home per week to save ~₹2,000/month.",
        "SHOPPING": f"💡 Tip: With ₹{amount:,.0f} in shopping, try the 24-hour rule before purchases over ₹500.",
        "ENTERTAINMENT": f"💡 Tip: Review your subscriptions. Are you using all streaming services worth ₹{amount:,.0f}?",
        "TRANSPORT": f"💡 Tip: For ₹{amount:,.0f} on transport, consider carpooling or metro for regular commutes.",
        "EMI": f"💡 Tip: EMIs at ₹{amount:,.0f}. Consider prepaying high-interest loans when you have surplus.",
    }
    return tips.get(category, f"💡 Keep tracking {category} spending for better insights.")


def get_investment_suggestions(savings_rate: float, monthly_surplus: float) -> List[Dict]:
    """Get investment suggestions based on savings rate."""
    suggestions = []
    
    if monthly_surplus <= 0:
        return [{
            "type": "Emergency",
            "message": "Focus on reducing expenses first. Build a 3-month emergency fund before investing.",
            "priority": "high"
        }]
    
    # Emergency fund first
    suggestions.append({
        "type": "Emergency Fund",
        "message": f"Keep ₹{monthly_surplus * 3:,.0f} (3 months expenses) in a savings account or liquid fund.",
        "priority": "high"
    })
    
    if savings_rate >= 10:
        suggestions.append({
            "type": "SIP",
            "message": f"Start a SIP of ₹{min(monthly_surplus * 0.5, 10000):,.0f}/month in an index fund.",
            "priority": "medium"
        })
    
    if savings_rate >= 20:
        suggestions.append({
            "type": "PPF/ELSS",
            "message": "Maximize tax-saving investments (Section 80C) with PPF or ELSS funds.",
            "priority": "medium"
        })
    
    if savings_rate >= 30:
        suggestions.append({
            "type": "Diversify",
            "message": "Consider diversifying into gold (SGBs) or NPS for additional tax benefits.",
            "priority": "low"
        })
    
    return suggestions


def generate_monthly_insights(
    df: pd.DataFrame,
    year: int,
    month: int,
    monthly_income: float = 0,
    user_name: str = "there",
    comparison_data: dict = None
) -> str:
    """
    Generate AI-powered insights for a specific month with month-over-month comparison.
    
    Args:
        df: DataFrame with transactions for the month
        year: Year of the month
        month: Month number (1-12)
        monthly_income: User's monthly income
        user_name: User's display name
        comparison_data: Optional dict with previous month comparison
    
    Returns:
        Markdown-formatted insights string
    """
    from calendar import month_name as cal_month_name
    
    if df.empty:
        return "📊 **No transaction data for this month.**"
    
    month_label = f"{cal_month_name[month]} {year}"
    
    # Gather analysis data
    patterns = analyze_spending_patterns(df, current_period_days=30, comparison_period_days=60)
    anomalies = detect_anomalies(df)
    savings = calculate_savings_potential(df, monthly_income)
    
    # Build enhanced context
    total_credit = df[df["direction"] == "CREDIT"]["amount"].sum()
    total_debit = df[df["direction"] == "DEBIT"]["amount"].sum()
    
    # Detailed merchant analysis
    merchant_details = df[df["direction"] == "DEBIT"].groupby("merchant_name").agg({
        "amount": ["sum", "count", "mean"]
    }).round(2)
    merchant_details.columns = ["total", "count", "avg"]
    merchant_details = merchant_details.sort_values("total", ascending=False).head(10)
    
    merchant_str = ""
    for name, row in merchant_details.iterrows():
        if name and name != "UNKNOWN":
            merchant_str += f"  - {name}: ₹{row['total']:,.0f} ({int(row['count'])} orders, avg ₹{row['avg']:,.0f})\n"
    
    # Category breakdown
    category_details = df[df["direction"] == "DEBIT"].groupby("category").agg({
        "amount": ["sum", "count"]
    }).round(2)
    category_details.columns = ["total", "count"]
    category_details = category_details.sort_values("total", ascending=False)
    category_details["pct"] = (category_details["total"] / category_details["total"].sum() * 100).round(1)
    
    category_str = ""
    for cat, row in category_details.iterrows():
        category_str += f"  - {cat}: ₹{row['total']:,.0f} ({row['pct']}%, {int(row['count'])} transactions)\n"
    
    # Build comparison context if available
    comparison_str = ""
    if comparison_data and comparison_data.get("has_previous_data"):
        prev_month = comparison_data["previous_month"]
        changes = comparison_data["changes"]
        cat_changes = comparison_data.get("category_changes", {})
        
        comparison_str = f"""
## MONTH-OVER-MONTH COMPARISON (vs {prev_month})
- Income Change: {changes.get('credit', 'N/A')}% {"↑" if (changes.get('credit') or 0) > 0 else "↓"}
- Spending Change: {changes.get('debit', 'N/A')}% {"↑" if (changes.get('debit') or 0) > 0 else "↓"}
- Net Difference: ₹{changes.get('net_diff', 0):+,.0f}

### Category Changes (biggest movements):
"""
        # Sort by absolute change
        sorted_cats = sorted(cat_changes.items(), key=lambda x: abs(x[1].get("change", 0)), reverse=True)
        for cat, data in sorted_cats[:5]:
            change = data.get("change", 0)
            if change != 0:
                arrow = "↑" if change > 0 else "↓"
                comparison_str += f"  - {cat}: {arrow} ₹{abs(change):,.0f} (was ₹{data['previous']:,.0f}, now ₹{data['current']:,.0f})\n"
    
    # Anomalies
    anomaly_str = ""
    for a in anomalies[:5]:
        anomaly_str += f"  - {a.merchant}: ₹{a.amount:,.0f} on {a.transaction_date} ({a.severity} - {a.reason})\n"
    
    context = f"""
## {month_label.upper()} FINANCIAL ANALYSIS

### SUMMARY
- Total Income: ₹{total_credit:,.0f}
- Total Spending: ₹{total_debit:,.0f}
- Net Savings: ₹{total_credit - total_debit:,.0f}
- Savings Rate: {savings.get('savings_rate', 0):.1f}%
- User's Monthly Income: ₹{monthly_income:,.0f}
- Total Transactions: {len(df)}

### SPENDING BY CATEGORY
{category_str}

### TOP MERCHANTS (with order frequency)
{merchant_str}
{comparison_str}

### UNUSUAL TRANSACTIONS
{anomaly_str if anomaly_str else "  - No unusual spending detected"}

### SPENDING CLASSIFICATION
- Essential Spending: ₹{savings.get('essential_spend', 0):,.0f}
- Discretionary Spending: ₹{savings.get('discretionary_spend', 0):,.0f}
"""
    
    try:
        model = _create_advisor_model()
        
        prompt = f"""
        Analyze the {month_label} spending data for {user_name}:
        
        {context}
        
        Provide specific, actionable insights following the exact response structure.
        Focus on:
        1. The biggest spending areas with exact merchant names and amounts
        2. Month-over-month changes (if comparison data available)
        3. 3 specific actions with calculated savings potential
        """
        
        response = model.generate_content(prompt)
        return response.text
        
    except Exception as e:
        # Fallback
        return f"""## 📊 {month_label} Summary

**Income:** ₹{total_credit:,.0f} | **Spending:** ₹{total_debit:,.0f} | **Saved:** ₹{total_credit - total_debit:,.0f}

### Top Spending Categories
{category_str}

### Top Merchants
{merchant_str}

*AI insights unavailable. Showing basic analysis.*
"""
