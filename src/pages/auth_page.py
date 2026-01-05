"""
Authentication pages for login and registration.
"""

import streamlit as st
from src.auth import login_user, register_user


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
