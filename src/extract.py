
# --- 3. THE "BRAIN" (Gemini Processor) ---
import json
import google.generativeai as genai
from src.models import MODEL_NAME, StatementAnalysis

MODEL_NAME = "gemini-2.5-flash"

# Optimized System Instruction (cached for reuse)
SYSTEM_INSTRUCTION = """
You are an expert Financial Data Extractor AI specializing in Indian bank statements.
Your task is to extract ALL transactions from this Bank Statement PDF with 100% accuracy.

## CRITICAL EXTRACTION RULES:

### 1. ROW DETECTION (MOST IMPORTANT)
- A transaction row ALWAYS starts with a DATE in format DD-MM-YYYY, DD/MM/YYYY, or similar
- Merge ALL text between dates into ONE transaction's description
- Include: Check numbers, Reference IDs, UTR numbers, transaction codes
- NEVER split a single transaction into multiple rows
- Watch for multi-line descriptions that wrap to next line

### 2. AMOUNT EXTRACTION
- Remove ALL commas from amounts (e.g., "1,234.56" → 1234.56)
- Amounts are pure floats, never strings
- If amount shows as "Dr" or in red/negative column → DEBIT
- If amount shows as "Cr" or in green/positive column → CREDIT

### 3. DIRECTION LOGIC
- "Deposits", "Credit", "Cr", positive → direction: "CREDIT"
- "Withdrawals", "Debit", "Dr", negative → direction: "DEBIT"
- UPI received = CREDIT, UPI sent = DEBIT

### 4. DATE HANDLING
- Normalize ALL dates to "YYYY-MM-DD" format
- If only day shown (continuation), use the last seen month/year

## CATEGORIZATION RULES (Match in order of priority):

| Category | Keywords/Patterns |
|----------|-------------------|
| SALARY | SALARY, PAYROLL, employer names |
| EMI | PIRAMAL, BAJAJ, MPOKKET, ACH DEBIT, LOAN, EMI, NACH |
| RENT | RENT, LEASE, LANDLORD, HOUSING |
| UTILITIES | ELECTRICITY, WATER, GAS, BROADBAND, AIRTEL, JIO, VI |
| FOOD | ZOMATO, SWIGGY, BLINKIT, ZEPTO, MC DONALDS, DOMINOS, KFC, RESTAURANT |
| GROCERIES | BIGBASKET, GROFERS, DMART, RELIANCE FRESH, SUPERMARKET |
| SHOPPING | AMAZON, FLIPKART, MYNTRA, AJIO, NYKAA, online shopping |
| TRANSPORT | UBER, OLA, RAPIDO, METRO, IRCTC, FUEL, PETROL, DIESEL |
| INVESTMENT | ZERODHA, GROWW, SIP, MUTUAL FUND, STOCKS, trading |
| ENTERTAINMENT | NETFLIX, PRIME, HOTSTAR, SPOTIFY, MOVIE, BOOKMYSHOW |
| MEDICAL | PHARMACY, HOSPITAL, DOCTOR, APOLLO, 1MG, PRACTO |
| TRANSFER | UPI, IMPS, NEFT, RTGS (person-to-person transfers) |
| ATM | ATM WITHDRAWAL, CASH WITHDRAWAL |
| BANK_CHARGES | SERVICE CHARGE, SMS ALERT, DEBIT CARD FEE, GST |
| UNCATEGORIZED | When no pattern matches |

## MERCHANT NAME EXTRACTION:
- Extract the actual merchant/payee name from description
- For UPI: Extract name after "UPI-" or before "@"
- For NEFT/IMPS: Extract beneficiary name
- If unclear, use "UNKNOWN"

## CONFIDENCE SCORING:
- 1.0: Clear, unambiguous extraction
- 0.8-0.9: Minor interpretation needed
- 0.5-0.7: Multiple possible interpretations
- Below 0.5: Guess/uncertain

## OUTPUT REQUIREMENTS:
- Extract EVERY transaction, do not skip any
- Empty transactions array if no transactions found
- account_holder: Extract from statement header
- statement_period: Extract date range from header
"""

def create_gemini_model():
    """Create and cache the Gemini model instance"""
    return genai.GenerativeModel(
        model_name=MODEL_NAME,
        system_instruction=SYSTEM_INSTRUCTION,
        generation_config=genai.GenerationConfig(
            response_mime_type="application/json",
            response_schema=StatementAnalysis,
            temperature=0.1,  # Low temperature for consistent extraction
        )
    )

# Create model instance once (reusable)
_model = None

def get_model():
    global _model
    if _model is None:
        _model = create_gemini_model()
    return _model


def analyze_chunk_with_gemini(pdf_path: str, chunk_index: int = 0, max_retries: int = 3):
    """
    Analyze a single PDF chunk with Gemini.
    
    Args:
        pdf_path: Path to the PDF chunk
        chunk_index: Index of this chunk (for logging)
        max_retries: Number of retry attempts on failure
    
    Returns:
        Parsed JSON response with transactions
    """
    import time
    
    for attempt in range(max_retries):
        try:
            print(f"[Chunk {chunk_index}] Uploading {pdf_path}...")
            
            # Upload the file to Gemini File API
            sample_file = genai.upload_file(
                path=pdf_path, 
                display_name=f"Bank Statement Chunk {chunk_index}"
            )
            
            try:
                print(f"[Chunk {chunk_index}] Analyzing transactions...")
                
                model = get_model()
                
                # Enhanced extraction prompt
                extraction_prompt = """
                Carefully analyze this bank statement page(s) and extract ALL transactions.
                
                IMPORTANT:
                - Do NOT skip any transaction, even if partially visible
                - Preserve the exact chronological order
                - For running balance, ignore it (we only need transaction amounts)
                - If this appears to be a continuation page, still extract account_holder as "CONTINUED" and statement_period as "PARTIAL"
                
                Extract every single transaction now.
                """
                
                response = model.generate_content([sample_file, extraction_prompt])
                
                result = json.loads(response.text)
                print(f"[Chunk {chunk_index}] ✓ Extracted {len(result.get('transactions', []))} transactions")
                return result
                
            finally:
                # Always cleanup uploaded file
                try:
                    genai.delete_file(sample_file.name)
                except:
                    pass
                    
        except Exception as e:
            print(f"[Chunk {chunk_index}] Attempt {attempt + 1} failed: {e}")
            if attempt < max_retries - 1:
                wait_time = (attempt + 1) * 2  # Exponential backoff
                print(f"[Chunk {chunk_index}] Retrying in {wait_time}s...")
                time.sleep(wait_time)
            else:
                print(f"[Chunk {chunk_index}] ✗ All retries failed")
                return {"account_holder": None, "statement_period": None, "transactions": []}
    
    return {"account_holder": None, "statement_period": None, "transactions": []}
