import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
from supabase import create_client
import io
import json

# Load environment variables
from dotenv import load_dotenv
import os

load_dotenv()

# Supabase configuration
SUPABASE_URL = os.getenv("SUPABASE_URL")
SUPABASE_KEY = os.getenv("SUPABASE_KEY")

# Initialize Supabase client
supabase = create_client(SUPABASE_URL, SUPABASE_KEY)

# Page config
st.set_page_config(page_title="Work Analytics Dashboard", layout="wide")

# Authentication functions
def create_user(username, password, role="user"):
    """Create a new user in Supabase"""
    try:
        response = supabase.table('users').insert({
            'username': username,
            'password': password,  # In production, use proper password hashing
            'role': role
        }).execute()
        return True
    except Exception as e:
        st.error(f"Error creating user: {str(e)}")
        return False

def check_credentials(username, password):
    """Verify user credentials"""
    try:
        response = supabase.table('users').select('*').eq('username', username).eq('password', password).execute()
        return len(response.data) > 0
    except Exception as e:
        st.error(f"Error checking credentials: {str(e)}")
        return False

def get_user_role(username):
    """Get user role from Supabase"""
    try:
        response = supabase.table('users').select('role').eq('username', username).execute()
        if response.data:
            return response.data[0]['role']
        return "user"
    except Exception as e:
        st.error(f"Error getting user role: {str(e)}")
        return "user"

# Data processing functions
def parse_duration(duration_str):
    """Convert duration string (e.g., '13m 6s') to minutes"""
    try:
        parts = duration_str.split()
        total_minutes = 0
        for part in parts:
            if 'm' in part:
                total_minutes += int(part.replace('m', ''))
            elif 's' in part:
                total_minutes += int(part.replace('s', '')) / 60
        return total_minutes
    except Exception as e:
        st.error(f"Error parsing duration: {duration_str}. Error: {str(e)}")
        return 0

def parse_amount(amount_str):
    """Convert amount string (e.g., '$5.73') to float"""
    try:
        return float(amount_str.replace('$', '').replace(',', ''))
    except Exception as e:
        st.error(f"Error parsing amount: {amount_str}. Error: {str(e)}")
        return 0.0

def validate_dataframe(df):
    """Validate that the dataframe has all required columns"""
    required_columns = {'workDate', 'duration', 'payout', 'payType', 'status'}
    missing_columns = required_columns - set(df.columns)
    
    if missing_columns:
        raise ValueError(f"Missing required columns: {missing_columns}")
    
    return True

def save_uploaded_data(df, username):
    """Save uploaded data to Supabase"""
    try:
        # Process the dataframe
        df['username'] = username
        df['workDate'] = pd.to_datetime(df['workDate'])
        df['duration_minutes'] = df['duration'].apply(parse_duration)
        df['payout_amount'] = df['payout'].apply(parse_amount)
        df['month_year'] = df['workDate'].dt.strftime('%Y-%m')
        
        # Convert timestamps to ISO format strings
        df['workDate'] = df['workDate'].dt.strftime('%Y-%m-%d')
        
        # Create a new DataFrame with exact column names matching the database
        data_to_save = {
            'username': df['username'],
            'workDate': df['workDate'],
            'duration': df['duration'],
            'duration_minutes': df['duration_minutes'],
            'payout': df['payout'],
            'payout_amount': df['payout_amount'],
            'payType': df['payType'],
            'status': df['status'],
            'month_year': df['month_year']
        }
        
        # Handle itemID if it exists
        if 'itemID' in df.columns:
            data_to_save['itemID'] = df['itemID']
        elif 'itemId' in df.columns:
            data_to_save['itemID'] = df['itemId']
        else:
            data_to_save['itemID'] = pd.Series([None] * len(df))
            
        # Create final DataFrame
        df_final = pd.DataFrame(data_to_save)
        
        # Convert to records and ensure all None values are properly handled
        records = df_final.replace({pd.NA: None}).to_dict('records')
        
        # Insert records into Supabase
        response = supabase.table('work_data').insert(records).execute()
        return True
        
    except Exception as e:
        st.error(f"Error saving data: {str(e)}")
        return False

def load_all_users_data():
    """Load all users' data from Supabase"""
    try:
        response = supabase.table('work_data').select('*').execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df['workDate'] = pd.to_datetime(df['workDate'])
            df['month_year'] = df['workDate'].dt.strftime('%Y-%m')
            return df
        return None
    except Exception as e:
        st.error(f"Error loading all data: {str(e)}")
        return None

def load_user_data(username):
    """Load specific user's data from Supabase"""
    try:
        response = supabase.table('work_data').select('*').eq('username', username).execute()
        if response.data:
            df = pd.DataFrame(response.data)
            df['workDate'] = pd.to_datetime(df['workDate'])
            df['month_year'] = df['workDate'].dt.strftime('%Y-%m')
            return df
        return None
    except Exception as e:
        st.error(f"Error loading user data: {str(e)}")
        return None

def calculate_user_metrics(df):
    """Calculate basic metrics for a user's data"""
    try:
        metrics = {
            'total_earnings': df['payout_amount'].sum(),
            'total_time_minutes': df['duration_minutes'].sum(),
            'days_worked': df['workDate'].nunique(),
            'average_earning': df['payout_amount'].mean(),
            'total_tasks': len(df)
        }
        return metrics
    except Exception as e:
        st.error(f"Error calculating metrics: {str(e)}")
        return {
            'total_earnings': 0,
            'total_time_minutes': 0,
            'days_worked': 0,
            'average_earning': 0,
            'total_tasks': 0
        }

def show_admin_dashboard(df):
    st.title("👑 Admin Dashboard")
    
    # Overall metrics
    total_earnings = df['payout_amount'].sum()
    total_time_minutes = df['duration_minutes'].sum()
    total_users = df['username'].nunique()
    
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Platform Earnings", f"${total_earnings:.2f}")
    with col2:
        hours = int(total_time_minutes // 60)
        minutes = int(total_time_minutes % 60)
        st.metric("Total Platform Time", f"{hours}h {minutes}m")
    with col3:
        st.metric("Total Active Users", total_users)

    # Month selector section
    st.subheader("Monthly Earnings Analysis")
    available_months = sorted(df['month_year'].unique())
    selected_month = st.selectbox("Select Month", available_months)
    
    # Filter data for selected month
    monthly_data = df[df['month_year'] == selected_month]
    
    # Calculate user earnings for selected month
    user_earnings = monthly_data.groupby('username')['payout_amount'].agg([
        ('total_earnings', 'sum'),
        ('tasks_completed', 'count'),
        ('average_per_task', lambda x: x.mean())
    ]).round(2)
    
    # Add hours worked
    user_earnings['hours_worked'] = monthly_data.groupby('username')['duration_minutes'].sum() / 60
    user_earnings['hours_worked'] = user_earnings['hours_worked'].round(1)
    
    # Calculate hourly rate
    user_earnings['hourly_rate'] = (user_earnings['total_earnings'] / user_earnings['hours_worked']).round(2)
    
    # Sort by total earnings
    user_earnings = user_earnings.sort_values('total_earnings', ascending=False)
    
    # Display monthly user earnings
    st.subheader(f"User Earnings - {selected_month}")
    
    # Format the dataframe for display
    display_df = user_earnings.copy()
    display_df.columns = ['Total Earnings ($)', 'Tasks Completed', 'Avg $/Task', 'Hours Worked', '$/Hour']
    
    # Add dollar signs to monetary columns
    display_df['Total Earnings ($)'] = display_df['Total Earnings ($)'].apply(lambda x: f"${x:,.2f}")
    display_df['Avg $/Task'] = display_df['Avg $/Task'].apply(lambda x: f"${x:,.2f}")
    display_df['$/Hour'] = display_df['$/Hour'].apply(lambda x: f"${x:,.2f}")
    
    st.dataframe(display_df, use_container_width=True)
    
    # Monthly Statistics
    st.subheader("Monthly Statistics")
    col1, col2, col3 = st.columns(3)
    
    with col1:
        st.metric("Total Monthly Earnings", f"${monthly_data['payout_amount'].sum():,.2f}")
    with col2:
        monthly_hours = monthly_data['duration_minutes'].sum() / 60
        st.metric("Total Hours Worked", f"{monthly_hours:,.1f}")
    with col3:
        avg_hourly = monthly_data['payout_amount'].sum() / (monthly_hours if monthly_hours > 0 else 1)
        st.metric("Average Hourly Rate", f"${avg_hourly:,.2f}")
    
    # Overall trends and visualizations section
    st.subheader("Overall Platform Trends")
    
    # Month-wise earnings per user
    monthly_earnings = df.pivot_table(
        index='username',
        columns='month_year',
        values='payout_amount',
        aggfunc='sum',
        fill_value=0
    ).round(2)
    
    # Add total column
    monthly_earnings['Total'] = monthly_earnings.sum(axis=1)
    
    # Sort by total earnings
    monthly_earnings = monthly_earnings.sort_values('Total', ascending=False)
    
    # Display monthly earnings table
    st.dataframe(monthly_earnings, use_container_width=True)
    
    # Monthly earnings trend chart
    monthly_trend = df.groupby(['month_year', 'username'])['payout_amount'].sum().reset_index()
    trend_chart = px.line(
        monthly_trend,
        x='month_year',
        y='payout_amount',
        color='username',
        title="Monthly Earnings Trend by User",
        labels={'month_year': 'Month', 'payout_amount': 'Earnings ($)', 'username': 'User'}
    )
    st.plotly_chart(trend_chart, use_container_width=True)
    
    # User Performance Analysis
    st.subheader("User Performance Overview")
    
    user_metrics = []
    for username in df['username'].unique():
        user_df = df[df['username'] == username]
        metrics = calculate_user_metrics(user_df)
        metrics['username'] = username
        metrics['avg_hourly_rate'] = (metrics['total_earnings'] / 
                                    (metrics['total_time_minutes'] / 60)
                                    if metrics['total_time_minutes'] > 0 else 0)
        user_metrics.append(metrics)
    
    user_metrics_df = pd.DataFrame(user_metrics)
    
    # Best performers section
    st.subheader("Top Performers")
    col1, col2 = st.columns(2)
    
    with col1:
        st.write("Highest Earnings")
        earnings_chart = px.bar(
            user_metrics_df.sort_values('total_earnings', ascending=False),
            x='username',
            y='total_earnings',
            title="Total Earnings by User"
        )
        st.plotly_chart(earnings_chart, use_container_width=True)
    
    with col2:
        st.write("Most Time Spent")
        time_chart = px.bar(
            user_metrics_df.sort_values('total_time_minutes', ascending=False),
            x='username',
            y='total_time_minutes',
            title="Total Time Spent by User (minutes)"
        )
        st.plotly_chart(time_chart, use_container_width=True)
    
    # Detailed user metrics table
    st.subheader("Detailed User Metrics")
    detailed_metrics = user_metrics_df.copy()
    detailed_metrics['avg_hourly_rate'] = detailed_metrics['avg_hourly_rate'].round(2)
    detailed_metrics['total_earnings'] = detailed_metrics['total_earnings'].round(2)
    
    # Fix the column ordering
    detailed_metrics = detailed_metrics[[
        'username',
        'total_earnings',
        'total_time_minutes',
        'days_worked',
        'average_earning',
        'total_tasks',
        'avg_hourly_rate'
    ]]
    
    # Rename columns
    detailed_metrics.columns = [
        'Username',
        'Total Earnings ($)',
        'Time Spent (mins)',
        'Days Worked',
        'Avg Earning/Task ($)',
        'Tasks Completed',
        'Avg Hourly Rate ($)'
    ]
    st.dataframe(detailed_metrics, use_container_width=True)

def show_user_dashboard(df):
    st.title("📊 Personal Dashboard")
    
    # Calculate metrics
    metrics = calculate_user_metrics(df)
    
    # Display key metrics
    col1, col2, col3 = st.columns(3)
    with col1:
        st.metric("Total Earnings", f"${metrics['total_earnings']:.2f}")
    with col2:
        hours = int(metrics['total_time_minutes'] // 60)
        minutes = int(metrics['total_time_minutes'] % 60)
        st.metric("Total Time Spent", f"{hours}h {minutes}m")
    with col3:
        avg_hourly = (metrics['total_earnings'] / (metrics['total_time_minutes'] / 60)
                     if metrics['total_time_minutes'] > 0 else 0)
        st.metric("Average Hourly Rate", f"${avg_hourly:.2f}")
    
    # Earnings over time
    st.subheader("Your Earnings Over Time")
    daily_earnings = df.groupby('workDate')['payout_amount'].sum().reset_index()
    earnings_chart = px.line(
        daily_earnings,
        x='workDate',
        y='payout_amount',
        title="Daily Earnings"
    )
    st.plotly_chart(earnings_chart, use_container_width=True)
    
    # Payment type breakdown
    st.subheader("Earnings by Payment Type")
    pay_type_data = df.groupby('payType')['payout_amount'].sum().reset_index()
    pay_type_chart = px.pie(
        pay_type_data,
        values='payout_amount',
        names='payType',
        title="Distribution of Earnings by Payment Type"
    )
    st.plotly_chart(pay_type_chart, use_container_width=True)
    
    # Recent activity
    st.subheader("Recent Activity")
    recent_df = df.sort_values('workDate', ascending=False).head(5)
    st.dataframe(recent_df[['workDate', 'duration', 'payout', 'payType', 'status']], 
                use_container_width=True)

def admin_panel():
    st.title("👑 Admin Panel")
    
    # User Management Section
    st.header("User Management")
    
    # Add New User
    st.subheader("Add New User")
    new_username = st.text_input("Username", key="new_user")
    new_password = st.text_input("Password", type="password", key="new_pass")
    
    if st.button("Add User"):
        if new_username and new_password:
            if create_user(new_username, new_password):
                st.success(f"User '{new_username}' created successfully!")
            else:
                st.error("Error creating user")
        else:
            st.error("Please fill in both fields")
    
    # View/Delete Users
    st.subheader("Existing Users")
    try:
        response = supabase.table('users').select('*').execute()
        if response.data:
            user_df = pd.DataFrame(response.data)
            st.dataframe(user_df[['username', 'role']], use_container_width=True)
            
            # Delete User
            non_admin_users = user_df[user_df['role'] != 'admin']['username'].tolist()
            user_to_delete = st.selectbox("Select user to delete", non_admin_users)
            
            if st.button("Delete User"):
                if user_to_delete:
                    try:
                        # Delete user's work data first
                        supabase.table('work_data').delete().eq('username', user_to_delete).execute()
                        # Then delete the user
                        supabase.table('users').delete().eq('username', user_to_delete).execute()
                        st.success(f"User '{user_to_delete}' deleted successfully!")
                        st.rerun()
                    except Exception as e:
                        st.error(f"Error deleting user: {str(e)}")
    except Exception as e:
        st.error(f"Error loading users: {str(e)}")

def show_dashboard():
    if not st.session_state.get('uploaded_file'):
        uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
        if uploaded_file:
            try:
                df = pd.read_csv(uploaded_file)
                validate_dataframe(df)
                if save_uploaded_data(df, st.session_state.username):
                    st.success("File uploaded and processed successfully!")
                    st.session_state.uploaded_file = uploaded_file
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                return
    
    if st.session_state.user_role == "admin":
        df = load_all_users_data()
    else:
        df = load_user_data(st.session_state.username)
    
    if df is not None:
        if st.session_state.user_role == "admin":
            show_admin_dashboard(df)
        else:
            show_user_dashboard(df)
        
        if st.button("Clear uploaded data"):
            try:
                if st.session_state.user_role != "admin":
                    supabase.table('work_data').delete().eq('username', st.session_state.username).execute()
                st.session_state.uploaded_file = None
                st.success("Data cleared successfully!")
                st.rerun()
            except Exception as e:
                st.error(f"Error clearing data: {str(e)}")
    else:
        st.info("No data available. Please upload a CSV file.")

def main():
    # Initialize all session states
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'show_admin' not in st.session_state:
        st.session_state.show_admin = False
    if 'user_role' not in st.session_state:
        st.session_state.user_role = None
    if 'username' not in st.session_state:
        st.session_state.username = None
    if 'uploaded_file' not in st.session_state:
        st.session_state.uploaded_file = None
    
    # Sidebar logout button if logged in
    if st.session_state.logged_in:
        if st.sidebar.button("Logout"):
            st.session_state.logged_in = False
            st.session_state.show_admin = False
            st.session_state.uploaded_file = None
            st.rerun()
    
    # Main login/dashboard logic
    if not st.session_state.logged_in:
        st.title("🔐 Login")
        
        username = st.text_input("Username")
        password = st.text_input("Password", type="password")
        
        if st.button("Login"):
            if check_credentials(username, password):
                st.session_state.logged_in = True
                st.session_state.username = username
                st.session_state.user_role = get_user_role(username)
                st.rerun()
            else:
                st.error("Invalid credentials")
    
    else:
        # Admin panel button in sidebar for admin users
        if st.session_state.user_role == "admin":
            if not st.session_state.show_admin and st.sidebar.button("Admin Panel"):
                st.session_state.show_admin = True
                st.rerun()
            elif st.session_state.show_admin and st.sidebar.button("Dashboard"):
                st.session_state.show_admin = False
                st.rerun()
        
        # Show appropriate view
        if st.session_state.show_admin and st.session_state.user_role == "admin":
            admin_panel()
        else:
            show_dashboard()

if __name__ == "__main__":
    main()