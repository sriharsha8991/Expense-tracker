"""
Upload page - handles bank statement PDF uploads and processing.
"""

import streamlit as st
import tempfile
import os
from datetime import datetime
from src.storage import save_transactions
from src.cache import (
    get_all_cached_statements, invalidate_cache, cache_statement
)
from main import process_statement


def show_upload_page():
    """Display the statement upload page."""
    st.title("📤 Upload Bank Statement")
    
    username = st.session_state.user["username"]
    
    # Bank selection
    col1, col2 = st.columns([2, 1])
    
    with col1:
        bank_name = st.selectbox(
            "Select Your Bank",
            options=["HDFC Bank", "ICICI Bank", "SBI", "Axis Bank", "Kotak Bank", "Other"],
            help="Select the bank that issued this statement"
        )
    
    with col2:
        if bank_name == "Other":
            bank_name = st.text_input("Enter Bank Name")
    
    # File upload
    uploaded_file = st.file_uploader(
        "Upload PDF Statement",
        type=["pdf"],
        help="Upload your bank statement in PDF format"
    )
    
    # Show cached statements
    cached = get_all_cached_statements(username)
    if cached:
        with st.expander(f"📁 Previously Processed Statements ({len(cached)})"):
            for stmt in cached:
                col1, col2, col3 = st.columns([3, 2, 1])
                with col1:
                    st.write(f"**{stmt['bank_name']}** - {stmt['statement_period']}")
                with col2:
                    st.write(f"{stmt['transaction_count']} transactions")
                with col3:
                    if st.button("🗑️", key=f"del_{stmt['statement_period']}"):
                        invalidate_cache(username, stmt['bank_name'], stmt['statement_period'])
                        st.rerun()
    
    if uploaded_file:
        st.divider()
        
        # Save uploaded file temporarily
        with tempfile.NamedTemporaryFile(delete=False, suffix=".pdf") as tmp_file:
            tmp_file.write(uploaded_file.read())
            tmp_path = tmp_file.name
        
        # Process button
        col1, col2 = st.columns([1, 1])
        
        with col1:
            force_reprocess = st.checkbox("Force Reprocess", help="Ignore cache and reprocess statement")
        
        with col2:
            process_btn = st.button("🚀 Process Statement", type="primary", use_container_width=True)
        
        if process_btn:
            try:
                # Progress container
                progress_bar = st.progress(0)
                status_text = st.empty()
                
                def update_progress(current: int, total: int, message: str):
                    progress_bar.progress(current / total)
                    status_text.text(message)
                
                # Process the statement
                with st.spinner("Processing statement with AI..."):
                    result = process_statement(
                        tmp_path,
                        max_workers=8,
                        pages_per_chunk=2,
                        progress_callback=update_progress
                    )
                
                # Extract data
                transactions = result.get("transactions", [])
                meta = result.get("meta", {})
                summary = result.get("summary", {})
                statement_period = meta.get("period", datetime.now().strftime("%Y-%m-%d"))
                
                if transactions:
                    # Save to user's CSV
                    new_count = save_transactions(username, transactions, bank_name, statement_period)
                    
                    # Cache the statement
                    cache_statement(
                        username=username,
                        bank_name=bank_name,
                        statement_period=statement_period,
                        transaction_count=len(transactions),
                        total_credit=summary.get("total_credit", 0),
                        total_debit=summary.get("total_debit", 0)
                    )
                    
                    st.success(f"""
                    ✅ **Processing Complete!**
                    - Extracted: {len(transactions)} transactions
                    - New transactions added: {new_count}
                    - Total Credit: ₹{summary.get('total_credit', 0):,.2f}
                    - Total Debit: ₹{summary.get('total_debit', 0):,.2f}
                    - Processing time: {meta.get('processing_time_seconds', 0):.1f}s
                    """)
                    
                    if st.button("📊 View Dashboard"):
                        st.session_state.current_page = "dashboard"
                        st.rerun()
                else:
                    st.warning("No transactions were extracted. Please check the PDF format.")
                    
            except Exception as e:
                st.error(f"Error processing statement: {str(e)}")
            
            finally:
                # Cleanup temp file
                try:
                    os.remove(tmp_path)
                except:
                    pass
