"""
Analyzer module for the Expense Tracker.
Provides spending pattern analysis and anomaly detection.
"""

import pandas as pd
from typing import Dict, Any, List, Optional
from datetime import datetime, timedelta
from dataclasses import dataclass


@dataclass
class SpendingPattern:
    """Represents a spending pattern insight."""
    category: str
    current_amount: float
    average_amount: float
    change_percent: float
    transaction_count: int
    trend: str  # "up", "down", "stable"
    

@dataclass
class Anomaly:
    """Represents a spending anomaly."""
    transaction_date: str
    description: str
    amount: float
    category: str
    merchant: str
    reason: str
    severity: str  # "low", "medium", "high"


def analyze_spending_patterns(
    df: pd.DataFrame, 
    current_period_days: int = 30,
    comparison_period_days: int = 90
) -> List[SpendingPattern]:
    """
    Analyze spending patterns by comparing current period to historical average.
    
    Args:
        df: DataFrame with all transactions
        current_period_days: Days in current analysis period
        comparison_period_days: Days for historical comparison
    
    Returns:
        List of SpendingPattern insights
    """
    if df.empty:
        return []
    
    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    
    today = datetime.now()
    current_start = today - timedelta(days=current_period_days)
    historical_start = today - timedelta(days=comparison_period_days)
    
    # Split data
    current = df[(df["transaction_date"] >= current_start) & (df["direction"] == "DEBIT")]
    historical = df[(df["transaction_date"] >= historical_start) & 
                    (df["transaction_date"] < current_start) & 
                    (df["direction"] == "DEBIT")]
    
    if current.empty:
        return []
    
    patterns = []
    
    # Analyze by category
    for category in current["category"].unique():
        current_cat = current[current["category"] == category]
        historical_cat = historical[historical["category"] == category]
        
        current_total = current_cat["amount"].sum()
        current_count = len(current_cat)
        
        # Calculate daily average for comparison
        current_daily_avg = current_total / current_period_days
        
        if not historical_cat.empty:
            historical_days = (current_start - historical_start).days
            historical_daily_avg = historical_cat["amount"].sum() / historical_days
            
            if historical_daily_avg > 0:
                change_percent = ((current_daily_avg - historical_daily_avg) / historical_daily_avg) * 100
            else:
                change_percent = 100.0 if current_daily_avg > 0 else 0.0
        else:
            historical_daily_avg = 0
            change_percent = 100.0 if current_daily_avg > 0 else 0.0
        
        # Determine trend
        if change_percent > 20:
            trend = "up"
        elif change_percent < -20:
            trend = "down"
        else:
            trend = "stable"
        
        patterns.append(SpendingPattern(
            category=category,
            current_amount=round(current_total, 2),
            average_amount=round(historical_daily_avg * current_period_days, 2),
            change_percent=round(change_percent, 1),
            transaction_count=current_count,
            trend=trend
        ))
    
    # Sort by absolute change
    patterns.sort(key=lambda x: abs(x.change_percent), reverse=True)
    
    return patterns


def detect_anomalies(
    df: pd.DataFrame,
    threshold_multiplier: float = 2.0
) -> List[Anomaly]:
    """
    Detect unusual transactions based on historical patterns.
    
    Args:
        df: DataFrame with transactions
        threshold_multiplier: Transactions above mean * multiplier are flagged
    
    Returns:
        List of Anomaly objects
    """
    if df.empty or len(df) < 5:
        return []
    
    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    
    debits = df[df["direction"] == "DEBIT"]
    if debits.empty:
        return []
    
    anomalies = []
    
    # Check by category
    for category in debits["category"].unique():
        cat_df = debits[debits["category"] == category]
        
        if len(cat_df) < 3:
            continue
        
        mean_amount = cat_df["amount"].mean()
        std_amount = cat_df["amount"].std()
        threshold = mean_amount + (threshold_multiplier * std_amount)
        
        # Find transactions above threshold
        unusual = cat_df[cat_df["amount"] > threshold]
        
        for _, row in unusual.iterrows():
            # Determine severity
            if row["amount"] > mean_amount * 5:
                severity = "high"
            elif row["amount"] > mean_amount * 3:
                severity = "medium"
            else:
                severity = "low"
            
            anomalies.append(Anomaly(
                transaction_date=row["transaction_date"].strftime("%Y-%m-%d"),
                description=row.get("description", "")[:100],
                amount=row["amount"],
                category=category,
                merchant=row.get("merchant_name", "UNKNOWN"),
                reason=f"Amount is {row['amount']/mean_amount:.1f}x higher than average ₹{mean_amount:,.0f} for {category}",
                severity=severity
            ))
    
    # Sort by amount descending
    anomalies.sort(key=lambda x: x.amount, reverse=True)
    
    return anomalies[:10]  # Return top 10


def calculate_savings_potential(
    df: pd.DataFrame,
    monthly_income: float = 0
) -> Dict[str, Any]:
    """
    Calculate potential savings based on spending patterns.
    
    Args:
        df: DataFrame with transactions
        monthly_income: User's monthly income
    
    Returns:
        Dict with savings analysis
    """
    if df.empty:
        return {
            "discretionary_spend": 0,
            "essential_spend": 0,
            "savings_rate": 0,
            "potential_savings": [],
            "monthly_budget_suggestion": {}
        }
    
    df = df.copy()
    debits = df[df["direction"] == "DEBIT"]
    credits = df[df["direction"] == "CREDIT"]
    
    total_income = credits["amount"].sum()
    total_spend = debits["amount"].sum()
    
    # Categorize as essential vs discretionary
    essential_categories = {"EMI", "RENT", "UTILITIES", "MEDICAL", "GROCERIES", "TRANSPORT"}
    discretionary_categories = {"FOOD", "SHOPPING", "ENTERTAINMENT", "TRANSFER", "UNCATEGORIZED"}
    
    essential_spend = debits[debits["category"].isin(essential_categories)]["amount"].sum()
    discretionary_spend = debits[debits["category"].isin(discretionary_categories)]["amount"].sum()
    
    # Calculate savings rate
    if monthly_income > 0:
        income_for_calc = monthly_income
    elif total_income > 0:
        income_for_calc = total_income
    else:
        income_for_calc = total_spend * 1.2  # Assume 20% more than spend
    
    current_savings = income_for_calc - total_spend
    savings_rate = (current_savings / income_for_calc * 100) if income_for_calc > 0 else 0
    
    # Identify potential savings
    potential_savings = []
    
    for category in discretionary_categories:
        cat_spend = debits[debits["category"] == category]["amount"].sum()
        if cat_spend > 0:
            # Suggest 20% reduction in discretionary spending
            potential = cat_spend * 0.2
            if potential > 500:  # Only suggest if meaningful amount
                potential_savings.append({
                    "category": category,
                    "current_spend": round(cat_spend, 2),
                    "suggested_reduction": round(potential, 2),
                    "tip": _get_savings_tip(category)
                })
    
    # Sort by potential savings
    potential_savings.sort(key=lambda x: x["suggested_reduction"], reverse=True)
    
    # Budget suggestion (50/30/20 rule)
    if income_for_calc > 0:
        budget_suggestion = {
            "needs": round(income_for_calc * 0.50, 2),
            "wants": round(income_for_calc * 0.30, 2),
            "savings": round(income_for_calc * 0.20, 2),
            "current_needs": round(essential_spend, 2),
            "current_wants": round(discretionary_spend, 2),
            "current_savings": round(current_savings, 2)
        }
    else:
        budget_suggestion = {}
    
    return {
        "discretionary_spend": round(discretionary_spend, 2),
        "essential_spend": round(essential_spend, 2),
        "total_spend": round(total_spend, 2),
        "total_income": round(total_income, 2),
        "savings_rate": round(savings_rate, 1),
        "potential_savings": potential_savings[:5],
        "monthly_budget_suggestion": budget_suggestion
    }


def _get_savings_tip(category: str) -> str:
    """Get a savings tip for a category."""
    tips = {
        "FOOD": "Try cooking at home more often. Meal prep on weekends can reduce food delivery costs by 50%.",
        "SHOPPING": "Wait 48 hours before non-essential purchases. Most impulse buys feel less necessary after a day.",
        "ENTERTAINMENT": "Look for free alternatives: public parks, library, free streaming tiers, or friend meetups.",
        "TRANSFER": "Review recurring transfers. Are all of them necessary? Consider consolidating subscriptions.",
        "UNCATEGORIZED": "Review these transactions to better categorize and track your spending."
    }
    return tips.get(category, "Review this category for potential savings.")


def get_spending_by_day_of_week(df: pd.DataFrame) -> Dict[str, float]:
    """Get average spending by day of week."""
    if df.empty:
        return {}
    
    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    debits = df[df["direction"] == "DEBIT"]
    
    if debits.empty:
        return {}
    
    debits["day"] = debits["transaction_date"].dt.day_name()
    daily_avg = debits.groupby("day")["amount"].mean()
    
    # Order by day
    day_order = ["Monday", "Tuesday", "Wednesday", "Thursday", "Friday", "Saturday", "Sunday"]
    result = {}
    for day in day_order:
        if day in daily_avg.index:
            result[day] = round(daily_avg[day], 2)
    
    return result


def get_monthly_comparison(df: pd.DataFrame) -> List[Dict]:
    """Get month-over-month spending comparison."""
    if df.empty:
        return []
    
    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"])
    df["month"] = df["transaction_date"].dt.to_period("M")
    
    monthly = df.groupby(["month", "direction"])["amount"].sum().unstack(fill_value=0)
    
    result = []
    for month in monthly.index:
        credit = monthly.loc[month].get("CREDIT", 0)
        debit = monthly.loc[month].get("DEBIT", 0)
        result.append({
            "month": str(month),
            "income": round(credit, 2),
            "spending": round(debit, 2),
            "savings": round(credit - debit, 2)
        })
    
    return result
