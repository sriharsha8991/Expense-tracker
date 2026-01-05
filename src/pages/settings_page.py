"""
Settings page - user profile, data management, and duplicate cleanup.
"""

import streamlit as st
from src.auth import update_user_profile
from src.storage import load_transactions, get_duplicate_summary, cleanup_duplicates
from src.cache import get_all_cached_statements


def show_settings_page():
    """Display user settings."""
    st.title("⚙️ Settings")
    
    user = st.session_state.user
    username = user["username"]
    
    st.markdown("### 👤 Profile")
    
    with st.form("profile_form"):
        display_name = st.text_input("Display Name", value=user.get("display_name", ""))
        monthly_income = st.number_input(
            "Monthly Income (₹)",
            min_value=0,
            value=int(user.get("monthly_income", 0)),
            step=1000,
            help="Used for calculating savings rate and budget recommendations"
        )
        
        if st.form_submit_button("Update Profile", use_container_width=True):
            success, message = update_user_profile(username, display_name, monthly_income)
            if success:
                st.session_state.user["display_name"] = display_name
                st.session_state.user["monthly_income"] = monthly_income
                st.success(message)
            else:
                st.error(message)
    
    st.divider()
    
    st.markdown("### 📊 Data Management")
    
    # Show stats
    df = load_transactions(username)
    if not df.empty:
        st.info(f"""
        **Your Data:**
        - Total Transactions: {len(df)}
        - Date Range: {df['transaction_date'].min()} to {df['transaction_date'].max()}
        - Banks: {', '.join(df['bank_name'].unique())}
        """)
        
        # Duplicate detection section
        st.markdown("#### 🔍 Duplicate Detection")
        
        col1, col2 = st.columns([1, 1])
        
        with col1:
            if st.button("🔎 Check for Duplicates", use_container_width=True):
                with st.spinner("Scanning for duplicates..."):
                    dup_summary = get_duplicate_summary(username)
                    st.session_state["dup_summary"] = dup_summary
        
        with col2:
            if st.button("🧹 Clean Up Duplicates", type="primary", use_container_width=True):
                with st.spinner("Removing duplicates..."):
                    result = cleanup_duplicates(username)
                    if result["removed"] > 0:
                        st.success(f"✅ Removed **{result['removed']}** duplicate transactions!")
                        st.session_state.pop("dup_summary", None)
                        st.rerun()
                    else:
                        st.info("No duplicates found!")
        
        # Show duplicate summary if available
        if "dup_summary" in st.session_state:
            dup_summary = st.session_state["dup_summary"]
            if dup_summary["duplicate_count"] > 0:
                st.warning(f"""
                **Found {dup_summary['duplicate_count']} duplicate groups** 
                ({dup_summary['total_duplicate_transactions']} extra transactions to remove)
                """)
                
                # Show sample duplicates
                with st.expander("🔍 Preview Duplicate Groups (first 5)", expanded=True):
                    for i, dup_group in enumerate(dup_summary["duplicates"][:5]):
                        st.markdown(f"**Group {i+1}** - {dup_group['count']} copies:")
                        for txn in dup_group["transactions"]:
                            st.markdown(f"  - `{txn.get('transaction_date', 'N/A')[:10]}` | ₹{txn.get('amount', 0):,.2f} | {txn.get('category', 'N/A')} | {txn.get('description', 'N/A')[:40]}...")
                        st.markdown("---")
            else:
                st.success("✅ No duplicates found! Your data is clean.")
    
    st.divider()
    
    # Clear cache option
    cached = get_all_cached_statements(username)
    if cached:
        if st.button("🗑️ Clear Processing Cache"):
            from src.cache import clear_all_cache
            clear_all_cache(username)
            st.success("Cache cleared!")
            st.rerun()
    
    st.divider()
    
    st.markdown("### ℹ️ About")
    st.markdown("""
    **Smart Expense Tracker** v1.0
    
    A personal money management tool that:
    - 📤 Extracts transactions from bank statement PDFs using AI
    - 📊 Provides visual spending analytics
    - 💡 Offers personalized financial recommendations
    - 📈 Helps you track and reduce unnecessary spending
    
    Built with ❤️ using Streamlit and Google Gemini AI.
    """)
