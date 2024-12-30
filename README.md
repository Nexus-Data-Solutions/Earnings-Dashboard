# Work Analytics Dashboard

A Streamlit dashboard for tracking and analyzing work data with user authentication and admin capabilities.

## Features

- User authentication system
- Admin dashboard with user management
- Data visualization with Plotly
- CSV file upload and processing
- Earnings analysis and metrics
- Payment type breakdown
- Time tracking

## Setup

1. Clone the repository:
```bash
git clone https://github.com/yourusername/work-analytics-dashboard.git
cd work-analytics-dashboard
```

2. Install dependencies:
```bash
pip install -r requirements.txt
```

3. Create a `.env` file with your Supabase credentials:
```env
SUPABASE_URL=your_supabase_url
SUPABASE_KEY=your_supabase_key
```

4. Run the application:
```bash
streamlit run app.py
```

## Database Setup

Run the following SQL commands in your Supabase SQL editor:

```sql
-- Create users table
CREATE TABLE users (
    id BIGSERIAL PRIMARY KEY,
    username TEXT UNIQUE NOT NULL,
    password TEXT NOT NULL,
    role TEXT NOT NULL DEFAULT 'user',
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create work_data table
CREATE TABLE work_data (
    id BIGSERIAL PRIMARY KEY,
    username TEXT REFERENCES users(username),
    workDate DATE NOT NULL,
    duration TEXT NOT NULL,
    duration_minutes FLOAT NOT NULL,
    payout TEXT NOT NULL,
    payout_amount FLOAT NOT NULL,
    payType TEXT NOT NULL,
    status TEXT NOT NULL,
    month_year TEXT NOT NULL,
    created_at TIMESTAMPTZ DEFAULT NOW()
);

-- Create initial admin user
INSERT INTO users (username, password, role) 
VALUES ('admin', 'admin123', 'admin');
```

## Usage

1. Login with admin credentials (username: admin, password: admin123)
2. Upload CSV files with work data
3. View analytics and manage users

## Security Notes

For production:
- Use proper password hashing
- Store credentials in environment variables
- Implement rate limiting
- Add input validation