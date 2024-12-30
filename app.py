import streamlit as st
import pandas as pd
import plotly.express as px
from datetime import datetime
import json
from pathlib import Path
import os

# Page config
st.set_page_config(page_title="Work Analytics Dashboard", layout="wide")

# Create necessary directories and files
Path("data").mkdir(exist_ok=True)
USERS_FILE = Path("data/users.json")

# Initialize users file with admin if it doesn't exist
if not USERS_FILE.exists():
    default_users = {
        "admin": {
            "password": "admin123",  # Change this in production
            "role": "admin"
        }
    }
    with open(USERS_FILE, "w") as f:
        json.dump(default_users, f)

# Authentication functions
def load_users():
    with open(USERS_FILE, "r") as f:
        return json.load(f)

def save_user(username, password, role="user"):
    users = load_users()
    users[username] = {
        "password": password,
        "role": role
    }
    with open(USERS_FILE, "w") as f:
        json.dump(users, f)

def check_credentials(username, password):
    users = load_users()
    return (username in users and 
            users[username]["password"] == password)

def get_user_role(username):
    users = load_users()
    return users.get(username, {}).get("role", "user")

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
    """Save uploaded data to user-specific CSV file"""
    data_dir = Path("data/user_data")
    data_dir.mkdir(exist_ok=True)
    
    # Always set the username column to ensure correct attribution
    df['username'] = username
    
    # Save to user-specific file
    file_path = data_dir / f"{username}_data.csv"
    df.to_csv(file_path, index=False)

def process_dataframe(df):
    """Process dataframe with all necessary transformations"""
    df['workDate'] = pd.to_datetime(df['workDate'])
    df['duration_minutes'] = df['duration'].apply(parse_duration)
    df['payout_amount'] = df['payout'].apply(parse_amount)
    return df

def load_all_users_data():
    """Load and combine data from all users"""
    data_dir = Path("data/user_data")
    data_dir.mkdir(exist_ok=True)
    
    all_data = []
    for file_path in data_dir.glob("*.csv"):
        try:
            df = pd.read_csv(file_path)
            df = process_dataframe(df)
            all_data.append(df)
        except Exception as e:
            st.error(f"Error loading {file_path.name}: {str(e)}")
    
    if all_data:
        combined_df = pd.concat(all_data, ignore_index=True)
        return combined_df
    return None

def load_user_data(username):
    """Load data for a specific user"""
    file_path = Path("data/user_data") / f"{username}_data.csv"
    if file_path.exists():
        try:
            df = pd.read_csv(file_path)
            df = process_dataframe(df)
            return df
        except Exception as e:
            st.error(f"Error loading user data: {str(e)}")
            return None
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

# Dashboard components
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
    # In the show_admin_dashboard function, update the detailed metrics section:

# Detailed user metrics table
    st.subheader("Detailed User Metrics")
    detailed_metrics = user_metrics_df.copy()
    detailed_metrics['avg_hourly_rate'] = detailed_metrics['avg_hourly_rate'].round(2)
    detailed_metrics['total_earnings'] = detailed_metrics['total_earnings'].round(2)
    
    # Fix the column ordering - ensure username appears first
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
            users = load_users()
            if new_username in users:
                st.error("Username already exists")
            else:
                save_user(new_username, new_password)
                st.success(f"User '{new_username}' created successfully!")
        else:
            st.error("Please fill in both fields")
    
    # View/Delete Users
    st.subheader("Existing Users")
    users = load_users()
    user_data = []
    
    for username, data in users.items():
        user_data.append({
            "Username": username,
            "Role": data["role"]
        })
    
    user_df = pd.DataFrame(user_data)
    st.dataframe(user_df, use_container_width=True)
    
    # Delete User
    user_to_delete = st.selectbox("Select user to delete", 
                                 [u["Username"] for u in user_data if u["Role"] != "admin"])
    if st.button("Delete User"):
        if user_to_delete:
            users = load_users()
            if users[user_to_delete]["role"] != "admin":
                del users[user_to_delete]
                with open(USERS_FILE, "w") as f:
                    json.dump(users, f)
                st.success(f"User '{user_to_delete}' deleted successfully!")
                st.rerun()

def show_dashboard():
    if not st.session_state.get('uploaded_file'):
        uploaded_file = st.file_uploader("Upload CSV File", type=["csv"])
        if uploaded_file:
            try:
                # Read and process the uploaded file
                df = pd.read_csv(uploaded_file)
                
                # Validate the dataframe
                validate_dataframe(df)
                
                # Process the dataframe
                df = process_dataframe(df)
                
                # Save the processed data
                save_uploaded_data(df, st.session_state.username)
                st.success("File uploaded and processed successfully!")
                st.session_state.uploaded_file = uploaded_file
                
            except Exception as e:
                st.error(f"Error processing file: {str(e)}")
                return
    
    # Load appropriate data based on user role
    if st.session_state.user_role == "admin":
        df = load_all_users_data()
    else:
        df = load_user_data(st.session_state.username)
    
    if df is not None:
        # Show appropriate dashboard based on user role
        if st.session_state.user_role == "admin":
            show_admin_dashboard(df)
        else:
            show_user_dashboard(df)
        
        # Option to clear uploaded file
        if st.button("Clear uploaded file"):
            if st.session_state.user_role != "admin":
                # Remove user's data file
                file_path = Path("data/user_data") / f"{st.session_state.username}_data.csv"
                if file_path.exists():
                    file_path.unlink()
            st.session_state.uploaded_file = None
            st.rerun()
    else:
        st.info("No data available. Please upload a CSV file.")

def main():
    # Initialize session states
    if 'logged_in' not in st.session_state:
        st.session_state.logged_in = False
    if 'show_admin' not in st.session_state:
        st.session_state.show_admin = False
    
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