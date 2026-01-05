"""
Authentication module for the Expense Tracker.
Handles user registration, login, and session management.
"""

import json
import os
import bcrypt
from pathlib import Path
from typing import Optional, Dict, Any
from datetime import datetime

# Data directory paths
DATA_DIR = Path(__file__).parent.parent / "data"
USERS_FILE = DATA_DIR / "users.json"
USERS_DATA_DIR = DATA_DIR / "users"


def _ensure_data_dirs():
    """Ensure data directories exist."""
    DATA_DIR.mkdir(exist_ok=True)
    USERS_DATA_DIR.mkdir(exist_ok=True)
    if not USERS_FILE.exists():
        with open(USERS_FILE, "w") as f:
            json.dump({"users": {}}, f)


def _load_users() -> Dict[str, Any]:
    """Load users from JSON file."""
    _ensure_data_dirs()
    try:
        with open(USERS_FILE, "r") as f:
            return json.load(f)
    except (json.JSONDecodeError, FileNotFoundError):
        return {"users": {}}


def _save_users(data: Dict[str, Any]):
    """Save users to JSON file."""
    _ensure_data_dirs()
    with open(USERS_FILE, "w") as f:
        json.dump(data, f, indent=2)


def hash_password(password: str) -> str:
    """Hash a password using bcrypt."""
    salt = bcrypt.gensalt()
    hashed = bcrypt.hashpw(password.encode('utf-8'), salt)
    return hashed.decode('utf-8')


def verify_password(password: str, hashed: str) -> bool:
    """Verify a password against its hash."""
    return bcrypt.checkpw(password.encode('utf-8'), hashed.encode('utf-8'))


def register_user(
    username: str, 
    password: str, 
    display_name: str,
    monthly_income: float = 0.0
) -> tuple[bool, str]:
    """
    Register a new user.
    
    Args:
        username: Unique username (lowercase, no spaces)
        password: User password (min 6 characters)
        display_name: Display name for the user
        monthly_income: Optional monthly income for budget calculations
    
    Returns:
        Tuple of (success: bool, message: str)
    """
    # Validation
    username = username.lower().strip()
    if not username or len(username) < 3:
        return False, "Username must be at least 3 characters"
    
    if " " in username:
        return False, "Username cannot contain spaces"
    
    if len(password) < 6:
        return False, "Password must be at least 6 characters"
    
    if not display_name.strip():
        return False, "Display name is required"
    
    # Check if user exists
    data = _load_users()
    if username in data["users"]:
        return False, "Username already exists"
    
    # Create user
    data["users"][username] = {
        "password_hash": hash_password(password),
        "display_name": display_name.strip(),
        "monthly_income": monthly_income,
        "created_at": datetime.now().isoformat(),
        "last_login": None
    }
    
    _save_users(data)
    
    # Create user data directory
    user_dir = USERS_DATA_DIR / username
    user_dir.mkdir(exist_ok=True)
    
    return True, "Registration successful!"


def login_user(username: str, password: str) -> tuple[bool, str, Optional[Dict]]:
    """
    Authenticate a user.
    
    Args:
        username: User's username
        password: User's password
    
    Returns:
        Tuple of (success: bool, message: str, user_data: Optional[Dict])
    """
    username = username.lower().strip()
    data = _load_users()
    
    if username not in data["users"]:
        return False, "Invalid username or password", None
    
    user = data["users"][username]
    
    if not verify_password(password, user["password_hash"]):
        return False, "Invalid username or password", None
    
    # Update last login
    data["users"][username]["last_login"] = datetime.now().isoformat()
    _save_users(data)
    
    # Return user data (without password hash)
    user_data = {
        "username": username,
        "display_name": user["display_name"],
        "monthly_income": user.get("monthly_income", 0),
        "created_at": user["created_at"]
    }
    
    return True, f"Welcome back, {user['display_name']}!", user_data


def get_user(username: str) -> Optional[Dict]:
    """Get user data by username."""
    data = _load_users()
    if username not in data["users"]:
        return None
    
    user = data["users"][username]
    return {
        "username": username,
        "display_name": user["display_name"],
        "monthly_income": user.get("monthly_income", 0),
        "created_at": user["created_at"],
        "last_login": user.get("last_login")
    }


def update_user_profile(
    username: str, 
    display_name: Optional[str] = None,
    monthly_income: Optional[float] = None
) -> tuple[bool, str]:
    """Update user profile information."""
    data = _load_users()
    
    if username not in data["users"]:
        return False, "User not found"
    
    if display_name is not None:
        data["users"][username]["display_name"] = display_name.strip()
    
    if monthly_income is not None:
        data["users"][username]["monthly_income"] = monthly_income
    
    _save_users(data)
    return True, "Profile updated successfully"


def get_user_data_dir(username: str) -> Path:
    """Get the data directory path for a user."""
    user_dir = USERS_DATA_DIR / username
    user_dir.mkdir(exist_ok=True)
    return user_dir
