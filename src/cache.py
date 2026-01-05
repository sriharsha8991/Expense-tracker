"""
Cache module for the Expense Tracker.
Tracks processed statements to avoid reprocessing.
"""

import json
import hashlib
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime
from src.auth import get_user_data_dir


def get_cache_file(username: str) -> Path:
    """Get the cache file path for a user."""
    return get_user_data_dir(username) / "cache.json"


def _load_cache(username: str) -> Dict[str, Any]:
    """Load cache from file."""
    cache_file = get_cache_file(username)
    if not cache_file.exists():
        return {"statements": {}}
    
    try:
        with open(cache_file, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"statements": {}}


def _save_cache(username: str, cache: Dict[str, Any]):
    """Save cache to file."""
    cache_file = get_cache_file(username)
    with open(cache_file, "w") as f:
        json.dump(cache, f, indent=2)


def generate_cache_key(bank_name: str, statement_period: str) -> str:
    """
    Generate a unique cache key for a statement.
    
    Args:
        bank_name: Name of the bank
        statement_period: Period string (e.g., "2025-12-01 to 2025-12-31")
    
    Returns:
        Hash-based cache key
    """
    key_string = f"{bank_name.lower().strip()}|{statement_period.strip()}"
    return hashlib.md5(key_string.encode()).hexdigest()[:16]


def is_statement_cached(username: str, bank_name: str, statement_period: str) -> bool:
    """
    Check if a statement has already been processed.
    
    Args:
        username: User's username
        bank_name: Name of the bank
        statement_period: Period string
    
    Returns:
        True if statement is cached, False otherwise
    """
    cache = _load_cache(username)
    cache_key = generate_cache_key(bank_name, statement_period)
    return cache_key in cache.get("statements", {})


def get_cached_statement(username: str, bank_name: str, statement_period: str) -> Optional[Dict]:
    """
    Get cached statement metadata.
    
    Returns:
        Dict with cached info or None if not cached
    """
    cache = _load_cache(username)
    cache_key = generate_cache_key(bank_name, statement_period)
    return cache.get("statements", {}).get(cache_key)


def cache_statement(
    username: str, 
    bank_name: str, 
    statement_period: str,
    transaction_count: int,
    total_credit: float,
    total_debit: float,
    file_hash: Optional[str] = None
):
    """
    Cache a processed statement.
    
    Args:
        username: User's username
        bank_name: Name of the bank
        statement_period: Period string
        transaction_count: Number of transactions extracted
        total_credit: Total credit amount
        total_debit: Total debit amount
        file_hash: Optional hash of the PDF file
    """
    cache = _load_cache(username)
    cache_key = generate_cache_key(bank_name, statement_period)
    
    cache.setdefault("statements", {})[cache_key] = {
        "bank_name": bank_name,
        "statement_period": statement_period,
        "transaction_count": transaction_count,
        "total_credit": total_credit,
        "total_debit": total_debit,
        "file_hash": file_hash,
        "processed_at": datetime.now().isoformat()
    }
    
    _save_cache(username, cache)


def invalidate_cache(username: str, bank_name: str, statement_period: str) -> bool:
    """
    Remove a statement from cache (for reprocessing).
    
    Returns:
        True if entry was removed, False if not found
    """
    cache = _load_cache(username)
    cache_key = generate_cache_key(bank_name, statement_period)
    
    if cache_key in cache.get("statements", {}):
        del cache["statements"][cache_key]
        _save_cache(username, cache)
        return True
    
    return False


def get_all_cached_statements(username: str) -> list[Dict]:
    """Get all cached statements for a user."""
    cache = _load_cache(username)
    return list(cache.get("statements", {}).values())


def clear_all_cache(username: str):
    """Clear all cache for a user."""
    cache = {"statements": {}}
    _save_cache(username, cache)


def get_file_hash(file_path: str) -> str:
    """Generate MD5 hash of a file for change detection."""
    hasher = hashlib.md5()
    with open(file_path, "rb") as f:
        for chunk in iter(lambda: f.read(8192), b""):
            hasher.update(chunk)
    return hasher.hexdigest()
