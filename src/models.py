import os
import google.generativeai as genai
import typing_extensions as typing
import json
from pydantic import BaseModel, Field

# --- CONFIGURATION ---
# Get key from https://aistudio.google.com/
# Prefer environment variable for security
GEMINI_API_KEY = os.environ.get("GEMINI_API_KEY", "Addyourapikey")
genai.configure(api_key=GEMINI_API_KEY)

# Use Flash for speed/cost, Pro for complex reasoning
MODEL_NAME = "gemini-2.5-flash"

# --- 1. DEFINE THE OUTPUT SCHEMA (Strict JSON) ---
# This forces Gemini to return ONLY this structure, no markdown parsing needed.

class TransactionItem(typing.TypedDict):
    transaction_date: str
    description: str
    amount: float
    direction: str  # CREDIT or DEBIT
    category: str
    merchant_name: str
    confidence_score: float


class StatementAnalysis(typing.TypedDict):
    account_holder: str
    statement_period: str
    transactions: list[TransactionItem]
