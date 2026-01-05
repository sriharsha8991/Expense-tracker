"""
Smart Expense Tracker - Streamlit App
A personal money manager with AI-powered insights.
"""

import streamlit as st
import pandas as pd
import tempfile
import os
from datetime import datetime, timedelta

# Page config must be first Streamlit command
st.set_page_config(
    page_title="Smart Expense Tracker",
    page_icon="💰",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Import our modules
from src.auth import login_user, register_user, get_user, update_user_profile
from src.storage import (
    load_transactions, save_transactions, filter_transactions_by_date,
    get_date_range_filter, get_transactions_summary, get_top_merchants,
    get_available_months, filter_by_month, get_month_comparison, get_monthly_trend
)
from src.cache import (
    is_statement_cached, cache_statement, invalidate_cache,
    get_all_cached_statements, get_file_hash
)
from src.dashboard import (
    create_spending_by_category_pie, create_spending_trend_line,
    create_category_bar_chart, create_merchant_bar_chart,
    create_credit_debit_comparison, create_weekly_heatmap,
    get_metric_cards_data, format_currency
)
from src.analyzer import (
    analyze_spending_patterns, detect_anomalies,
    calculate_savings_potential, get_monthly_comparison as analyzer_monthly_comparison
)
from src.insights import generate_spending_insights, get_investment_suggestions, generate_monthly_insights
from main import process_statement


# --- Session State Initialization ---
def init_session_state():
    """Initialize session state variables."""
    if "authenticated" not in st.session_state:
        st.session_state.authenticated = False
    if "user" not in st.session_state:
        st.session_state.user = None
    if "current_page" not in st.session_state:
        st.session_state.current_page = "dashboard"


init_session_state()


# --- Custom CSS ---
st.markdown("""
<style>
    .metric-card {
        background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
        padding: 1rem;
        border-radius: 0.5rem;
        color: white;
        text-align: center;
    }
    .stMetric > div {
        background-color: #f8fafc;
        padding: 1rem;
        border-radius: 0.5rem;
        border: 1px solid #e2e8f0;
    }
    .success-box {
        background-color: #d1fae5;
        border-left: 4px solid #10b981;
        padding: 1rem;
        border-radius: 0.25rem;
    }
    .warning-box {
        background-color: #fef3c7;
        border-left: 4px solid #f59e0b;
        padding: 1rem;
        border-radius: 0.25rem;
    }
    .info-box {
        background-color: #dbeafe;
        border-left: 4px solid #3b82f6;
        padding: 1rem;
        border-radius: 0.25rem;
    }
</style>
""", unsafe_allow_html=True)


# --- Authentication Pages ---
def show_login_page():
    """Display the login page."""
    st.title("💰 Smart Expense Tracker")
    st.markdown("### Your Personal Money Manager")
    
    tab1, tab2 = st.tabs(["🔐 Login", "📝 Register"])
    
    with tab1:
        with st.form("login_form"):
            username = st.text_input("Username")
            password = st.text_input("Password", type="password")
            submit = st.form_submit_button("Login", use_container_width=True)
            
            if submit:
                if username and password:
                    success, message, user_data = login_user(username, password)
                    if success:
                        st.session_state.authenticated = True
                        st.session_state.user = user_data
                        st.success(message)
                        st.rerun()
                    else:
                        st.error(message)
                else:
                    st.warning("Please enter both username and password")
    
    with tab2:
        with st.form("register_form"):
            new_username = st.text_input("Choose Username")
            new_password = st.text_input("Choose Password", type="password")
            confirm_password = st.text_input("Confirm Password", type="password")
            display_name = st.text_input("Your Name")
            monthly_income = st.number_input("Monthly Income (₹)", min_value=0, value=0, step=1000)
            
            register = st.form_submit_button("Create Account", use_container_width=True)
            
            if register:
                if new_password != confirm_password:
                    st.error("Passwords do not match")
                elif not new_username or not new_password or not display_name:
                    st.warning("Please fill all required fields")
                else:
                    success, message = register_user(
                        new_username, new_password, display_name, monthly_income
                    )
                    if success:
                        st.success(message + " Please login now.")
                    else:
                        st.error(message)


def show_sidebar():
    """Display the sidebar navigation."""
    with st.sidebar:
        st.title(f"👋 Hello, {st.session_state.user['display_name']}!")
        
        st.divider()
        
        # Navigation
        pages = {
            "📊 Dashboard": "dashboard",
            "� Monthly Analysis": "monthly",
            "📤 Upload Statement": "upload",
            "💡 AI Insights": "insights",
            "📋 Transactions": "transactions",
            "⚙️ Settings": "settings"
        }
        
        for label, page in pages.items():
            if st.button(label, use_container_width=True, 
                        type="primary" if st.session_state.current_page == page else "secondary"):
                st.session_state.current_page = page
                st.rerun()
        
        st.divider()
        
        # Time Period Selection
        st.markdown("### 📅 Time Period")
        
        # Load user transactions to get available months
        username = st.session_state.user["username"]
        df = load_transactions(username)
        available_months = get_available_months(df) if not df.empty else []
        
        # Filter mode toggle
        filter_mode = st.radio(
            "Select by",
            options=["relative", "specific_month"],
            format_func=lambda x: "Relative Period" if x == "relative" else "Specific Month",
            horizontal=True,
            key="filter_mode"
        )
        
        if filter_mode == "relative":
            time_range = st.selectbox(
                "Period",
                options=["week", "2weeks", "month", "6months"],
                format_func=lambda x: {
                    "week": "Last 7 days",
                    "2weeks": "Last 2 weeks",
                    "month": "Last 30 days",
                    "6months": "Last 6 months"
                }[x],
                key="time_range"
            )
            st.session_state.selected_month_data = None
        else:
            if available_months:
                # Month selector
                month_options = {f"{m['month_name']} ({m['transaction_count']} txns)": m for m in available_months}
                selected_label = st.selectbox(
                    "Select Month",
                    options=list(month_options.keys()),
                    key="month_selector"
                )
                st.session_state.selected_month_data = month_options[selected_label]
            else:
                st.info("📤 Upload statements to see months")
                st.session_state.selected_month_data = None
        
        st.divider()
        
        if st.button("🚪 Logout", use_container_width=True):
            st.session_state.authenticated = False
            st.session_state.user = None
            st.rerun()


# --- Main Pages ---
def show_dashboard_page():
    """Display the main dashboard."""
    st.title("📊 Financial Dashboard")
    
    # Load transactions
    username = st.session_state.user["username"]
    df = load_transactions(username)
    
    if df.empty:
        st.info("👋 Welcome! Upload your first bank statement to get started.")
        if st.button("📤 Upload Statement"):
            st.session_state.current_page = "upload"
            st.rerun()
        return
    
    # Apply time filter based on mode
    filter_mode = st.session_state.get("filter_mode", "relative")
    selected_month = st.session_state.get("selected_month_data")
    
    if filter_mode == "specific_month" and selected_month:
        # Filter by specific month
        filtered_df = filter_by_month(df, selected_month["year"], selected_month["month"])
        period_label = selected_month["month_name"]
    else:
        # Relative time range
        time_range = st.session_state.get("time_range", "month")
        start_date, end_date = get_date_range_filter(time_range)
        filtered_df = filter_transactions_by_date(df, start_date, end_date)
        period_label = {
            "week": "Last 7 days",
            "2weeks": "Last 2 weeks",
            "month": "Last 30 days",
            "6months": "Last 6 months"
        }.get(time_range, "Selected Period")
    
    st.caption(f"📅 Showing data for: **{period_label}**")
    
    if filtered_df.empty:
        st.warning(f"No transactions found for {period_label}.")
        return
    
    # Metric cards
    metrics = get_metric_cards_data(filtered_df, st.session_state.user.get("monthly_income", 0))
    
    cols = st.columns(4)
    for i, metric in enumerate(metrics):
        with cols[i]:
            prefix = metric.get("prefix", "")
            st.metric(
                label=metric["label"],
                value=f"{prefix}{metric['value']}",
                delta=metric.get("delta")
            )
    
    st.divider()
    
    # Charts row 1
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            create_spending_by_category_pie(filtered_df, "DEBIT"),
            use_container_width=True
        )
    
    with col2:
        st.plotly_chart(
            create_credit_debit_comparison(filtered_df),
            use_container_width=True
        )
    
    # Charts row 2
    st.plotly_chart(
        create_spending_trend_line(filtered_df),
        use_container_width=True
    )
    
    # Charts row 3
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            create_category_bar_chart(filtered_df, "DEBIT"),
            use_container_width=True
        )
    
    with col2:
        st.plotly_chart(
            create_merchant_bar_chart(filtered_df),
            use_container_width=True
        )


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


def show_insights_page():
    """Display AI-powered insights."""
    st.title("💡 AI Financial Insights")
    
    username = st.session_state.user["username"]
    df = load_transactions(username)
    
    if df.empty:
        st.info("Upload bank statements to get personalized insights.")
        return
    
    # Apply time filter
    time_range = st.session_state.get("time_range", "month")
    start_date, end_date = get_date_range_filter(time_range)
    filtered_df = filter_transactions_by_date(df, start_date, end_date)
    
    # Generate insights button
    if st.button("🔄 Generate Fresh Insights", type="primary"):
        with st.spinner("Analyzing your spending patterns..."):
            insights = generate_spending_insights(
                filtered_df,
                st.session_state.user.get("monthly_income", 0),
                st.session_state.user.get("display_name", "there")
            )
            st.session_state.last_insights = insights
    
    # Display insights
    if "last_insights" in st.session_state:
        st.markdown(st.session_state.last_insights)
    else:
        # Show basic analysis
        st.markdown("### 📈 Spending Patterns")
        
        patterns = analyze_spending_patterns(filtered_df)
        if patterns:
            for pattern in patterns[:5]:
                icon = "📈" if pattern.trend == "up" else "📉" if pattern.trend == "down" else "➡️"
                change_text = f"+{pattern.change_percent:.0f}%" if pattern.change_percent > 0 else f"{pattern.change_percent:.0f}%"
                st.markdown(f"{icon} **{pattern.category}**: ₹{pattern.current_amount:,.0f} ({change_text} vs average)")
    
    st.divider()
    
    # Savings potential
    st.markdown("### 💰 Savings Potential")
    
    savings = calculate_savings_potential(filtered_df, st.session_state.user.get("monthly_income", 0))
    
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Essential Spending", f"₹{savings['essential_spend']:,.0f}")
    with col2:
        st.metric("Discretionary Spending", f"₹{savings['discretionary_spend']:,.0f}")
    with col3:
        st.metric("Savings Rate", f"{savings['savings_rate']:.1f}%")
    
    # Potential savings suggestions
    if savings.get("potential_savings"):
        st.markdown("#### 💡 Where You Could Save")
        for saving in savings["potential_savings"]:
            with st.expander(f"**{saving['category']}** - Save ₹{saving['suggested_reduction']:,.0f}/month"):
                st.write(f"Current spend: ₹{saving['current_spend']:,.0f}")
                st.info(saving["tip"])
    
    st.divider()
    
    # Investment suggestions
    st.markdown("### 📊 Investment Suggestions")
    
    monthly_surplus = savings.get("total_income", 0) - savings.get("total_spend", 0)
    suggestions = get_investment_suggestions(savings["savings_rate"], monthly_surplus)
    
    for suggestion in suggestions:
        priority_color = {"high": "🔴", "medium": "🟡", "low": "🟢"}
        st.markdown(f"{priority_color.get(suggestion['priority'], '⚪')} **{suggestion['type']}**: {suggestion['message']}")
    
    st.divider()
    
    # Anomalies
    st.markdown("### ⚠️ Unusual Transactions")
    
    anomalies = detect_anomalies(filtered_df)
    if anomalies:
        for anomaly in anomalies[:5]:
            severity_icon = {"high": "🔴", "medium": "🟠", "low": "🟡"}
            st.warning(f"""
            {severity_icon.get(anomaly.severity, '⚪')} **{anomaly.merchant}** - ₹{anomaly.amount:,.0f}
            
            {anomaly.reason}
            """)
    else:
        st.success("No unusual transactions detected. Your spending looks consistent! 👍")


def show_transactions_page():
    """Display all transactions with filters."""
    st.title("📋 All Transactions")
    
    username = st.session_state.user["username"]
    df = load_transactions(username)
    
    if df.empty:
        st.info("No transactions yet. Upload a bank statement to get started.")
        return
    
    # Get available months
    available_months = get_available_months(df)
    
    # Filter mode selector
    col1, col2, col3 = st.columns([2, 1, 1])
    with col1:
        filter_mode = st.radio(
            "Filter by",
            options=["all", "time_period", "specific_month"],
            format_func=lambda x: {
                "all": "Show All",
                "time_period": "Time Period (7d, 30d, etc.)",
                "specific_month": "Specific Month (Oct, Nov, etc.)"
            }[x],
            horizontal=True,
            key="transactions_filter_mode"
        )
    
    # Filters
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        categories = ["All"] + list(df["category"].unique())
        selected_category = st.selectbox("📁 Category", categories)
    
    with col2:
        directions = ["All", "💰 Income", "💸 Spending"]
        selected_direction = st.selectbox("Type", directions)
    
    with col3:
        search = st.text_input("🔍 Search", placeholder="Description or merchant...")
    
    with col4:
        min_amount = st.number_input("Min Amount (₹)", value=0, step=100)
    
    # Apply filters
    filtered = df.copy()
    
    if selected_category != "All":
        filtered = filtered[filtered["category"] == selected_category]
    
    if selected_direction != "All":
        direction_map = {"💰 Income": "CREDIT", "💸 Spending": "DEBIT"}
        selected_direction_code = direction_map.get(selected_direction, selected_direction)
        filtered = filtered[filtered["direction"] == selected_direction_code]
    
    if search:
        filtered = filtered[filtered["description"].str.contains(search, case=False, na=False)]
    
    if min_amount > 0:
        filtered = filtered[filtered["amount"] >= min_amount]
    
    # Apply time filter based on mode
    if filter_mode == "time_period":
        time_range = st.session_state.get("time_range", "month")
        start_date, end_date = get_date_range_filter(time_range)
        filtered = filter_transactions_by_date(filtered, start_date, end_date)
        period_info = f"({time_range.replace('6months', 'Last 6 months').replace('month', 'Last 30 days').replace('2weeks', 'Last 2 weeks').replace('week', 'Last 7 days')})"
    elif filter_mode == "specific_month":
        if available_months:
            month_options = {m['month_name']: m for m in available_months}
            selected_month_label = st.selectbox(
                "📆 Select Month",
                options=list(month_options.keys()),
                key="transactions_month_selector"
            )
            selected_month = month_options[selected_month_label]
            filtered = filter_by_month(filtered, selected_month["year"], selected_month["month"])
            period_info = f"({selected_month['month_name']})"
        else:
            period_info = ""
    else:
        period_info = "(All transactions)"
    
    # Display summary with period info
    st.markdown(f"### Showing **{len(filtered)}** transactions {period_info}")
    
    # Display transactions
    if not filtered.empty:
        # Sort by date descending (newest first)
        filtered = filtered.sort_values("transaction_date", ascending=False)
        
        # Format for display
        display_df = filtered[["transaction_date", "description", "amount", "direction", "category", "merchant_name"]].copy()
        display_df["transaction_date"] = pd.to_datetime(display_df["transaction_date"]).dt.strftime("%Y-%m-%d")
        
        # Color code by direction
        display_df["Type"] = display_df["direction"].apply(lambda x: "💰 Credit" if x == "CREDIT" else "💸 Debit")
        display_df["Amount (₹)"] = display_df["amount"].apply(lambda x: f"₹{x:,.2f}")
        
        display_df = display_df.rename(columns={
            "transaction_date": "Date",
            "description": "Description",
            "category": "Category",
            "merchant_name": "Merchant"
        })
        
        display_df = display_df[["Date", "Description", "Amount (₹)", "Type", "Category", "Merchant"]]
        
        st.dataframe(
            display_df,
            use_container_width=True,
            height=500,
            hide_index=True
        )
        
        # Statistics
        st.divider()
        col1, col2, col3, col4 = st.columns(4)
        
        total_debit = filtered[filtered["direction"] == "DEBIT"]["amount"].sum()
        total_credit = filtered[filtered["direction"] == "CREDIT"]["amount"].sum()
        net = total_credit - total_debit
        avg_transaction = filtered["amount"].mean()
        
        with col1:
            st.metric("💸 Total Spending", f"₹{total_debit:,.0f}")
        
        with col2:
            st.metric("💰 Total Income", f"₹{total_credit:,.0f}")
        
        with col3:
            st.metric("📈 Net", f"₹{net:,.0f}", delta=f"avg: ₹{avg_transaction:,.0f}")
        
        with col4:
            transaction_count = len(filtered)
            st.metric("📊 Count", transaction_count, delta=f"avg: ₹{avg_transaction:,.0f}")
        
        # Export option
        st.divider()
        csv = filtered.to_csv(index=False)
        st.download_button(
            "📥 Download CSV",
            csv,
            file_name=f"transactions_{username}_{datetime.now().strftime('%Y%m%d')}.csv",
            mime="text/csv"
        )
    else:
        st.warning(f"No transactions found matching your filters {period_info}")



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
        
        from src.storage import get_duplicate_summary, cleanup_duplicates
        
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


def show_monthly_analysis_page():
    """Display detailed monthly analysis with month-over-month comparison."""
    st.title("📅 Monthly Analysis")
    
    username = st.session_state.user["username"]
    df = load_transactions(username)
    
    if df.empty:
        st.info("📤 Upload bank statements to see monthly analysis.")
        return
    
    # Get available months
    available_months = get_available_months(df)
    
    if not available_months:
        st.warning("No monthly data available yet.")
        return
    
    # Month selector at top of page
    col1, col2 = st.columns([2, 1])
    
    with col1:
        month_options = {m['month_name']: m for m in available_months}
        selected_label = st.selectbox(
            "📆 Select Month to Analyze",
            options=list(month_options.keys()),
            key="monthly_analysis_selector"
        )
        selected = month_options[selected_label]
    
    with col2:
        st.markdown("###")  # Spacing
        generate_ai = st.button("🤖 Generate AI Analysis", type="primary", use_container_width=True)
    
    year, month = selected["year"], selected["month"]
    
    # Get comparison data
    comparison = get_month_comparison(df, year, month)
    month_df = filter_by_month(df, year, month)
    
    st.divider()
    
    # Summary metrics with comparison
    st.subheader(f"📊 {comparison['current_month']} Overview")
    
    col1, col2, col3, col4 = st.columns(4)
    
    with col1:
        delta_str = None
        if comparison["has_previous_data"] and comparison["changes"]["credit"]:
            delta_str = f"{comparison['changes']['credit']:+.1f}%"
        st.metric(
            "💰 Income",
            f"₹{comparison['current']['credit']:,.0f}",
            delta=delta_str
        )
    
    with col2:
        delta_str = None
        if comparison["has_previous_data"] and comparison["changes"]["debit"]:
            delta_str = f"{comparison['changes']['debit']:+.1f}%"
        st.metric(
            "💸 Spending",
            f"₹{comparison['current']['debit']:,.0f}",
            delta=delta_str,
            delta_color="inverse"
        )
    
    with col3:
        st.metric(
            "💵 Net Savings",
            f"₹{comparison['current']['net']:,.0f}",
            delta=f"₹{comparison['changes']['net_diff']:+,.0f}" if comparison["has_previous_data"] else None
        )
    
    with col4:
        savings_rate = 0
        if comparison['current']['credit'] > 0:
            savings_rate = (comparison['current']['net'] / comparison['current']['credit']) * 100
        st.metric(
            "📈 Savings Rate",
            f"{savings_rate:.1f}%"
        )
    
    st.divider()
    
    # Month-over-month comparison section
    if comparison["has_previous_data"]:
        st.subheader(f"📈 Compared to {comparison['previous_month']}")
        
        # Category changes - sorted by absolute change
        cat_changes = comparison["category_changes"]
        sorted_cats = sorted(cat_changes.items(), key=lambda x: abs(x[1].get("change", 0)), reverse=True)
        
        # Show increases and decreases
        col1, col2 = st.columns(2)
        
        with col1:
            st.markdown("##### 🔺 Increased Spending")
            increases = [(cat, data) for cat, data in sorted_cats if data["change"] > 0]
            if increases:
                for cat, data in increases[:5]:
                    pct = data.get("change_pct")
                    pct_str = f" ({pct:+.0f}%)" if pct else ""
                    st.markdown(f"**{cat}**: ₹{data['current']:,.0f} (+₹{data['change']:,.0f}){pct_str}")
            else:
                st.success("No categories increased! 🎉")
        
        with col2:
            st.markdown("##### 🔻 Decreased Spending")
            decreases = [(cat, data) for cat, data in sorted_cats if data["change"] < 0]
            if decreases:
                for cat, data in decreases[:5]:
                    pct = data.get("change_pct")
                    pct_str = f" ({pct:.0f}%)" if pct else ""
                    st.markdown(f"**{cat}**: ₹{data['current']:,.0f} (-₹{abs(data['change']):,.0f}){pct_str}")
            else:
                st.info("No decreases this month")
    else:
        st.info(f"ℹ️ No data for {comparison['previous_month']} to compare against.")
    
    st.divider()
    
    # Charts for the month
    col1, col2 = st.columns(2)
    
    with col1:
        st.plotly_chart(
            create_spending_by_category_pie(month_df, "DEBIT"),
            use_container_width=True
        )
    
    with col2:
        st.plotly_chart(
            create_merchant_bar_chart(month_df),
            use_container_width=True
        )
    
    # Top merchants table
    st.subheader("🏪 Top Merchants This Month")
    if comparison["top_merchants"]:
        merchant_data = []
        for m in comparison["top_merchants"]:
            merchant_data.append({
                "Merchant": m["name"],
                "Total Spent": f"₹{m['amount']:,.0f}",
                "Transactions": m["count"],
                "Avg per Transaction": f"₹{m['amount']/m['count']:,.0f}"
            })
        st.dataframe(merchant_data, use_container_width=True, hide_index=True)
    
    st.divider()
    
    # AI Insights section
    st.subheader("🤖 AI-Powered Monthly Insights")
    
    if generate_ai or f"monthly_insights_{year}_{month}" in st.session_state:
        if generate_ai:
            with st.spinner(f"Analyzing {selected['month_name']}..."):
                insights = generate_monthly_insights(
                    month_df,
                    year,
                    month,
                    st.session_state.user.get("monthly_income", 0),
                    st.session_state.user.get("display_name", "there"),
                    comparison
                )
                st.session_state[f"monthly_insights_{year}_{month}"] = insights
        
        if f"monthly_insights_{year}_{month}" in st.session_state:
            st.markdown(st.session_state[f"monthly_insights_{year}_{month}"])
    else:
        st.info("👆 Click 'Generate AI Analysis' for personalized insights about this month's spending.")
    
    st.divider()
    
    # Monthly trend chart (last 6 months)
    st.subheader("📊 Monthly Spending Trend")
    trend_data = get_monthly_trend(df, num_months=6)
    
    if trend_data:
        import plotly.graph_objects as go
        
        fig = go.Figure()
        
        months = [t["month"] for t in trend_data]
        credits = [t["credit"] for t in trend_data]
        debits = [t["debit"] for t in trend_data]
        nets = [t["net"] for t in trend_data]
        
        fig.add_trace(go.Bar(
            name="💰 Income",
            x=months,
            y=credits,
            marker=dict(
                color="#10B981",
                line=dict(color="white", width=2)
            ),
            text=[f"₹{v:,.0f}" for v in credits],
            textposition="outside",
            textfont=dict(size=9, color="#1F2937"),
            hovertemplate="<b>%{x}</b><br>💰 Income: ₹%{y:,.0f}<extra></extra>"
        ))
        
        fig.add_trace(go.Bar(
            name="💸 Spending",
            x=months,
            y=debits,
            marker=dict(
                color="#EF4444",
                line=dict(color="white", width=2)
            ),
            text=[f"₹{v:,.0f}" for v in debits],
            textposition="outside",
            textfont=dict(size=9, color="#1F2937"),
            hovertemplate="<b>%{x}</b><br>💸 Spending: ₹%{y:,.0f}<extra></extra>"
        ))
        
        fig.add_trace(go.Scatter(
            name="📈 Net Savings",
            x=months,
            y=nets,
            mode="lines+markers+text",
            line=dict(color="#06B6D4", width=3, shape="spline"),
            fill="tozeroy",
            fillcolor="rgba(6, 182, 212, 0.15)",
            marker=dict(
                size=12,
                symbol="circle",
                line=dict(color="white", width=2),
                color="#06B6D4"
            ),
            text=[f"₹{v:,.0f}" for v in nets],
            textposition="top center",
            textfont=dict(size=10, color="#1F2937"),
            hovertemplate="<b>%{x}</b><br>📈 Net: ₹%{y:,.0f}<extra></extra>"
        ))
        
        fig.update_layout(
            barmode="group",
            title=dict(
                text="💹 Income vs Spending Trend (Last 6 Months)",
                font=dict(size=18, family="Arial Black, sans-serif", color="#1F2937"),
                x=0.5,
                xanchor="center"
            ),
            xaxis_title="Month",
            yaxis_title="Amount (₹)",
            height=420,
            legend=dict(
                orientation="h",
                yanchor="bottom",
                y=1.02,
                xanchor="right",
                x=1,
                bgcolor="rgba(255, 255, 255, 0.8)",
                bordercolor="#6B7280",
                borderwidth=1
            ),
            margin=dict(t=80, b=60, l=70, r=20),
            paper_bgcolor="#F3F4F6",
            plot_bgcolor="#FFFFFF",
            xaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(107, 114, 128, 0.1)"),
            yaxis=dict(showgrid=True, gridwidth=1, gridcolor="rgba(107, 114, 128, 0.1)"),
            font=dict(family="Arial, sans-serif", size=10)
        )
        
        st.plotly_chart(fig, use_container_width=True)


# --- Main App ---
def main():
    """Main application entry point."""
    if not st.session_state.authenticated:
        show_login_page()
    else:
        show_sidebar()
        
        # Route to current page
        page = st.session_state.current_page
        
        if page == "dashboard":
            show_dashboard_page()
        elif page == "monthly":
            show_monthly_analysis_page()
        elif page == "upload":
            show_upload_page()
        elif page == "insights":
            show_insights_page()
        elif page == "transactions":
            show_transactions_page()
        elif page == "settings":
            show_settings_page()


if __name__ == "__main__":
    main()
