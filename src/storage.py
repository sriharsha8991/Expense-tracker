"""
Storage module for the Expense Tracker.
Handles CSV transaction storage and JSON data persistence.
"""

import json
import csv
import re
import pandas as pd
from pathlib import Path
from typing import List, Dict, Any, Optional
from datetime import datetime
from src.auth import get_user_data_dir


def get_user_transactions_file(username: str) -> Path:
    """Get the transactions CSV file path for a user."""
    return get_user_data_dir(username) / "transactions.csv"


def get_user_cache_file(username: str) -> Path:
    """Get the cache JSON file path for a user."""
    return get_user_data_dir(username) / "cache.json"


# --- Deduplication Utilities ---

def normalize_description(description: str) -> str:
    """
    Normalize a transaction description for comparison.
    Removes extra spaces, special chars, and standardizes case.
    """
    if not description:
        return ""
    
    # Convert to lowercase
    text = description.lower()
    
    # Remove common suffixes that LLM might add/omit
    removals = [
        r'\d{2,4}[-/]\d{2}[-/]\d{2,4}',  # Dates
        r'ref\s*[:.-]?\s*\w+',  # Reference numbers
        r'txn\s*[:.-]?\s*\w+',  # Transaction IDs
        r'utr\s*[:.-]?\s*\w+',  # UTR numbers
        r'\*+\d+',  # Masked card numbers
        r'#\w+',  # Reference tags
    ]
    
    for pattern in removals:
        text = re.sub(pattern, '', text, flags=re.IGNORECASE)
    
    # Remove special characters except alphanumeric and spaces
    text = re.sub(r'[^a-z0-9\s]', ' ', text)
    
    # Normalize whitespace
    text = ' '.join(text.split())
    
    # Take first 50 chars (main identifier)
    return text[:50].strip()


def generate_dedup_key(row: Dict) -> str:
    """
    Generate a deduplication key for a transaction.
    Uses date + amount + normalized description core.
    """
    date_str = str(row.get("transaction_date", ""))[:10]  # YYYY-MM-DD
    amount = float(row.get("amount", 0))
    # Round amount to handle float precision
    amount_str = f"{amount:.2f}"
    
    # Get first significant words from description
    desc = normalize_description(row.get("description", ""))
    # Take first 3 words as the core identifier
    words = desc.split()[:3]
    desc_core = "_".join(words) if words else "unknown"
    
    return f"{date_str}_{amount_str}_{desc_core}"


def deduplicate_transactions(df: pd.DataFrame, keep: str = "first") -> pd.DataFrame:
    """
    Remove duplicate transactions based on smart matching.
    
    Args:
        df: DataFrame with transactions
        keep: 'first' to keep first occurrence, 'last' to keep last, 'best' to keep highest confidence
    
    Returns:
        Deduplicated DataFrame
    """
    if df.empty:
        return df
    
    # Generate deduplication keys
    df = df.copy()
    df["_dedup_key"] = df.apply(generate_dedup_key, axis=1)
    
    if keep == "best":
        # Keep the one with highest confidence score
        df = df.sort_values("confidence_score", ascending=False)
        df = df.drop_duplicates(subset=["_dedup_key"], keep="first")
    else:
        df = df.drop_duplicates(subset=["_dedup_key"], keep=keep)
    
    # Remove the helper column
    df = df.drop(columns=["_dedup_key"])
    
    return df


def find_duplicates(df: pd.DataFrame) -> pd.DataFrame:
    """
    Find duplicate transactions for review.
    
    Returns:
        DataFrame with potential duplicates grouped together
    """
    if df.empty:
        return df
    
    df = df.copy()
    df["_dedup_key"] = df.apply(generate_dedup_key, axis=1)
    
    # Find keys that appear more than once
    dup_keys = df["_dedup_key"].value_counts()
    dup_keys = dup_keys[dup_keys > 1].index.tolist()
    
    duplicates = df[df["_dedup_key"].isin(dup_keys)].copy()
    duplicates = duplicates.sort_values(["_dedup_key", "imported_at"])
    duplicates = duplicates.drop(columns=["_dedup_key"])
    
    return duplicates


# --- Transaction CSV Operations ---

TRANSACTION_COLUMNS = [
    "transaction_id",
    "transaction_date",
    "description",
    "amount",
    "direction",
    "category",
    "merchant_name",
    "confidence_score",
    "bank_name",
    "statement_period",
    "imported_at"
]


def save_transactions(username: str, transactions: List[Dict], bank_name: str, statement_period: str) -> int:
    """
    Save transactions to user's CSV file.
    Appends new transactions, avoiding duplicates using smart matching.
    
    Args:
        username: User's username
        transactions: List of transaction dicts
        bank_name: Name of the bank
        statement_period: Statement period string
    
    Returns:
        Number of new transactions added
    """
    csv_path = get_user_transactions_file(username)
    existing_df = load_transactions(username)
    
    # Prepare new transactions
    new_records = []
    imported_at = datetime.now().isoformat()
    
    for txn in transactions:
        # Generate a more robust transaction_id
        dedup_key = generate_dedup_key(txn)
        record = {
            "transaction_id": dedup_key,
            "transaction_date": txn.get("transaction_date"),
            "description": txn.get("description"),
            "amount": txn.get("amount"),
            "direction": txn.get("direction"),
            "category": txn.get("category"),
            "merchant_name": txn.get("merchant_name"),
            "confidence_score": txn.get("confidence_score", 0.0),
            "bank_name": bank_name,
            "statement_period": statement_period,
            "imported_at": imported_at
        }
        new_records.append(record)
    
    new_df = pd.DataFrame(new_records)
    
    if existing_df.empty:
        combined_df = new_df
    else:
        # Combine existing and new
        combined_df = pd.concat([existing_df, new_df], ignore_index=True)
    
    # Count before deduplication
    count_before = len(combined_df)
    
    # Apply smart deduplication - keep first (existing) or best (highest confidence)
    combined_df = deduplicate_transactions(combined_df, keep="best")
    
    count_after = len(combined_df)
    duplicates_removed = count_before - count_after
    
    if duplicates_removed > 0:
        print(f"Removed {duplicates_removed} duplicate transactions")
        
    # Sort by date
    combined_df["transaction_date"] = pd.to_datetime(combined_df["transaction_date"], errors="coerce")
    combined_df = combined_df.sort_values("transaction_date", ascending=False)
    combined_df["transaction_date"] = combined_df["transaction_date"].dt.strftime("%Y-%m-%d")
    
    # Save to CSV
    combined_df.to_csv(csv_path, index=False)
    
    new_count = len(combined_df) - len(existing_df) if not existing_df.empty else len(combined_df)
    return max(0, new_count)


def cleanup_duplicates(username: str) -> Dict[str, int]:
    """
    Clean up duplicate transactions for a user.
    
    Returns:
        Dict with cleanup statistics
    """
    csv_path = get_user_transactions_file(username)
    df = load_transactions(username)
    
    if df.empty:
        return {"original_count": 0, "final_count": 0, "removed": 0}
    
    original_count = len(df)
    
    # Find duplicates for reporting
    duplicates = find_duplicates(df)
    
    # Deduplicate keeping best (highest confidence)
    df = deduplicate_transactions(df, keep="best")
    
    final_count = len(df)
    removed = original_count - final_count
    
    if removed > 0:
        # Save cleaned data
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        df = df.sort_values("transaction_date", ascending=False)
        df["transaction_date"] = df["transaction_date"].dt.strftime("%Y-%m-%d")
        df.to_csv(csv_path, index=False)
    
    return {
        "original_count": original_count,
        "final_count": final_count,
        "removed": removed,
        "duplicate_groups": len(duplicates["_dedup_key"].unique()) if "_dedup_key" in duplicates.columns else 0
    }


def get_duplicate_summary(username: str) -> Dict[str, Any]:
    """
    Get a summary of potential duplicates without removing them.
    
    Returns:
        Dict with duplicate info
    """
    df = load_transactions(username)
    
    if df.empty:
        return {"total_transactions": 0, "duplicates": [], "duplicate_count": 0}
    
    df = df.copy()
    df["_dedup_key"] = df.apply(generate_dedup_key, axis=1)
    
    # Find duplicate keys
    dup_counts = df["_dedup_key"].value_counts()
    dup_keys = dup_counts[dup_counts > 1]
    
    duplicates = []
    for key, count in dup_keys.items():
        dups = df[df["_dedup_key"] == key].to_dict("records")
        duplicates.append({
            "key": key,
            "count": count,
            "transactions": dups
        })
    
    return {
        "total_transactions": len(df),
        "duplicates": duplicates[:20],  # Limit to first 20 groups
        "duplicate_count": len(dup_keys),
        "total_duplicate_transactions": dup_counts[dup_counts > 1].sum() - len(dup_keys)  # Extra copies
    }


def load_transactions(username: str) -> pd.DataFrame:
    """
    Load all transactions for a user.
    
    Returns:
        DataFrame with all transactions, or empty DataFrame if none exist
    """
    csv_path = get_user_transactions_file(username)
    
    if not csv_path.exists():
        return pd.DataFrame(columns=TRANSACTION_COLUMNS)
    
    try:
        df = pd.read_csv(csv_path)
        # Ensure date column is properly typed
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
        return df
    except Exception as e:
        print(f"Error loading transactions: {e}")
        return pd.DataFrame(columns=TRANSACTION_COLUMNS)


def filter_transactions_by_date(
    df: pd.DataFrame, 
    start_date: Optional[datetime] = None,
    end_date: Optional[datetime] = None
) -> pd.DataFrame:
    """Filter transactions by date range."""
    if df.empty:
        return df
    
    # Ensure transaction_date is datetime
    if df["transaction_date"].dtype == "object":
        df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    
    if start_date:
        df = df[df["transaction_date"] >= pd.to_datetime(start_date)]
    
    if end_date:
        df = df[df["transaction_date"] <= pd.to_datetime(end_date)]
    
    return df


def get_date_range_filter(range_type: str) -> tuple[datetime, datetime]:
    """
    Get start and end dates for predefined ranges.
    
    Args:
        range_type: One of 'week', '2weeks', 'month', '6months'
    
    Returns:
        Tuple of (start_date, end_date)
    """
    from datetime import timedelta
    
    end_date = datetime.now()
    
    if range_type == "week":
        start_date = end_date - timedelta(days=7)
    elif range_type == "2weeks":
        start_date = end_date - timedelta(days=14)
    elif range_type == "month":
        start_date = end_date - timedelta(days=30)
    elif range_type == "6months":
        start_date = end_date - timedelta(days=180)
    else:
        # Default to month
        start_date = end_date - timedelta(days=30)
    
    return start_date, end_date


def get_transactions_summary(df: pd.DataFrame) -> Dict[str, Any]:
    """
    Get summary statistics for transactions.
    
    Returns:
        Dict with summary stats
    """
    if df.empty:
        return {
            "total_transactions": 0,
            "total_credit": 0.0,
            "total_debit": 0.0,
            "net_flow": 0.0,
            "category_breakdown": {},
            "daily_breakdown": {}
        }
    
    total_credit = df[df["direction"] == "CREDIT"]["amount"].sum()
    total_debit = df[df["direction"] == "DEBIT"]["amount"].sum()
    
    # Category breakdown
    category_breakdown = {}
    for category in df["category"].unique():
        cat_df = df[df["category"] == category]
        category_breakdown[category] = {
            "count": len(cat_df),
            "total": round(cat_df["amount"].sum(), 2),
            "credit": round(cat_df[cat_df["direction"] == "CREDIT"]["amount"].sum(), 2),
            "debit": round(cat_df[cat_df["direction"] == "DEBIT"]["amount"].sum(), 2)
        }
    
    # Daily breakdown (for charts)
    daily_df = df.copy()
    daily_df["date"] = daily_df["transaction_date"].dt.date
    daily_breakdown = daily_df.groupby("date").agg({
        "amount": "sum",
        "transaction_id": "count"
    }).to_dict("index")
    
    return {
        "total_transactions": len(df),
        "total_credit": round(total_credit, 2),
        "total_debit": round(total_debit, 2),
        "net_flow": round(total_credit - total_debit, 2),
        "category_breakdown": category_breakdown,
        "daily_breakdown": {str(k): v for k, v in daily_breakdown.items()}
    }


def get_top_merchants(df: pd.DataFrame, top_n: int = 10, direction: str = "DEBIT") -> List[Dict]:
    """Get top merchants by spend."""
    if df.empty:
        return []
    
    filtered = df[df["direction"] == direction]
    if filtered.empty:
        return []
    
    merchant_totals = filtered.groupby("merchant_name")["amount"].agg(["sum", "count"])
    merchant_totals = merchant_totals.sort_values("sum", ascending=False).head(top_n)
    
    return [
        {"merchant": name, "total": round(row["sum"], 2), "count": int(row["count"])}
        for name, row in merchant_totals.iterrows()
        if name and name != "UNKNOWN"
    ]


def delete_transactions_by_period(username: str, statement_period: str, bank_name: str) -> int:
    """Delete transactions for a specific statement period (for reprocessing)."""
    df = load_transactions(username)
    if df.empty:
        return 0
    
    original_count = len(df)
    df = df[~((df["statement_period"] == statement_period) & (df["bank_name"] == bank_name))]
    
    csv_path = get_user_transactions_file(username)
    df.to_csv(csv_path, index=False)
    
    return original_count - len(df)


# --- Monthly Analysis Functions ---

def get_available_months(df: pd.DataFrame) -> List[Dict[str, Any]]:
    """
    Get list of months available in the transaction data.
    
    Returns:
        List of dicts with year, month, month_name, transaction_count
    """
    if df.empty:
        return []
    
    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df = df.dropna(subset=["transaction_date"])
    
    if df.empty:
        return []
    
    df["year_month"] = df["transaction_date"].dt.to_period("M")
    
    monthly_counts = df.groupby("year_month").size().reset_index(name="count")
    
    months = []
    for _, row in monthly_counts.iterrows():
        period = row["year_month"]
        months.append({
            "year": period.year,
            "month": period.month,
            "month_name": period.strftime("%B %Y"),
            "period": str(period),
            "transaction_count": row["count"]
        })
    
    # Sort by date descending (most recent first)
    months.sort(key=lambda x: (x["year"], x["month"]), reverse=True)
    return months


def filter_by_month(df: pd.DataFrame, year: int, month: int) -> pd.DataFrame:
    """Filter transactions for a specific month."""
    if df.empty:
        return df
    
    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    
    return df[
        (df["transaction_date"].dt.year == year) & 
        (df["transaction_date"].dt.month == month)
    ]


def get_month_comparison(df: pd.DataFrame, year: int, month: int) -> Dict[str, Any]:
    """
    Compare a specific month to the previous month.
    
    Returns:
        Dict with current month stats, previous month stats, and changes
    """
    from calendar import month_name as cal_month_name
    
    current = filter_by_month(df, year, month)
    
    # Calculate previous month
    if month == 1:
        prev_year, prev_month = year - 1, 12
    else:
        prev_year, prev_month = year, month - 1
    
    previous = filter_by_month(df, prev_year, prev_month)
    
    def calc_stats(data: pd.DataFrame) -> Dict[str, float]:
        if data.empty:
            return {"credit": 0, "debit": 0, "net": 0, "transactions": 0}
        return {
            "credit": round(data[data["direction"] == "CREDIT"]["amount"].sum(), 2),
            "debit": round(data[data["direction"] == "DEBIT"]["amount"].sum(), 2),
            "net": round(
                data[data["direction"] == "CREDIT"]["amount"].sum() - 
                data[data["direction"] == "DEBIT"]["amount"].sum(), 2
            ),
            "transactions": len(data)
        }
    
    current_stats = calc_stats(current)
    previous_stats = calc_stats(previous)
    
    # Calculate percentage changes
    def pct_change(current_val: float, previous_val: float) -> Optional[float]:
        if previous_val == 0:
            return None if current_val == 0 else 100.0
        return round(((current_val - previous_val) / previous_val) * 100, 1)
    
    # Category comparison
    current_by_cat = {}
    previous_by_cat = {}
    
    if not current.empty:
        current_by_cat = current[current["direction"] == "DEBIT"].groupby("category")["amount"].sum().to_dict()
    if not previous.empty:
        previous_by_cat = previous[previous["direction"] == "DEBIT"].groupby("category")["amount"].sum().to_dict()
    
    all_categories = set(current_by_cat.keys()) | set(previous_by_cat.keys())
    category_changes = {}
    
    for cat in all_categories:
        curr_val = current_by_cat.get(cat, 0)
        prev_val = previous_by_cat.get(cat, 0)
        category_changes[cat] = {
            "current": round(curr_val, 2),
            "previous": round(prev_val, 2),
            "change": round(curr_val - prev_val, 2),
            "change_pct": pct_change(curr_val, prev_val)
        }
    
    # Top merchants for current month
    top_merchants = []
    if not current.empty:
        debits = current[current["direction"] == "DEBIT"]
        if not debits.empty:
            merchant_totals = debits.groupby("merchant_name")["amount"].agg(["sum", "count"])
            merchant_totals = merchant_totals.sort_values("sum", ascending=False).head(5)
            top_merchants = [
                {"name": name, "amount": round(row["sum"], 2), "count": int(row["count"])}
                for name, row in merchant_totals.iterrows()
                if name and name != "UNKNOWN"
            ]
    
    return {
        "current_month": f"{cal_month_name[month]} {year}",
        "previous_month": f"{cal_month_name[prev_month]} {prev_year}",
        "current": current_stats,
        "previous": previous_stats,
        "has_previous_data": previous_stats["transactions"] > 0,
        "changes": {
            "credit": pct_change(current_stats["credit"], previous_stats["credit"]),
            "debit": pct_change(current_stats["debit"], previous_stats["debit"]),
            "net_diff": round(current_stats["net"] - previous_stats["net"], 2)
        },
        "category_changes": category_changes,
        "top_merchants": top_merchants
    }


def get_monthly_trend(df: pd.DataFrame, num_months: int = 6) -> List[Dict[str, Any]]:
    """
    Get spending trend for the last N months.
    
    Returns:
        List of monthly stats ordered by date
    """
    from calendar import month_name as cal_month_name
    
    if df.empty:
        return []
    
    df = df.copy()
    df["transaction_date"] = pd.to_datetime(df["transaction_date"], errors="coerce")
    df = df.dropna(subset=["transaction_date"])
    
    if df.empty:
        return []
    
    df["year_month"] = df["transaction_date"].dt.to_period("M")
    
    # Get unique months and sort
    months = df["year_month"].unique()
    months = sorted(months, reverse=True)[:num_months]
    
    trend = []
    for period in reversed(months):
        month_df = df[df["year_month"] == period]
        credit = month_df[month_df["direction"] == "CREDIT"]["amount"].sum()
        debit = month_df[month_df["direction"] == "DEBIT"]["amount"].sum()
        
        trend.append({
            "month": period.strftime("%b %Y"),
            "month_short": period.strftime("%b"),
            "year": period.year,
            "month_num": period.month,
            "credit": round(credit, 2),
            "debit": round(debit, 2),
            "net": round(credit - debit, 2),
            "transactions": len(month_df)
        })
    
    return trend
