import sqlite3
import os
from datetime import datetime

DB_PATH = "users.db"

def get_db_connection():
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    return conn

def init_db():
    """Initialize the database and create the users table if it doesn't exist."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute('''
        CREATE TABLE IF NOT EXISTS users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            email TEXT UNIQUE NOT NULL,
            password_hash TEXT,
            name TEXT,
            picture TEXT,
            daily_checks INTEGER DEFAULT 0,
            last_check_date TEXT,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    ''')
    
    # MIGRATION: Check if column exists, if not add it
    try:
        cursor.execute("SELECT daily_checks FROM users LIMIT 1")
    except sqlite3.OperationalError:
        cursor.execute("ALTER TABLE users ADD COLUMN daily_checks INTEGER DEFAULT 0")
        cursor.execute("ALTER TABLE users ADD COLUMN last_check_date TEXT")
    
    conn.commit()
    conn.close()

def sync_user_data(email, name=None, picture=None):
    """
    Ensures user exists in DB and returns their usage data.
    Resets daily_checks if the date has changed.
    """
    today = datetime.now().strftime("%Y-%m-%d")
    conn = get_db_connection()
    cursor = conn.cursor()
    
    # Check if user exists
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    row = cursor.fetchone()
    
    if not row:
        # Create new entry
        cursor.execute(
            "INSERT INTO users (email, name, picture, daily_checks, last_check_date) VALUES (?, ?, ?, ?, ?)",
            (email, name, picture, 0, today)
        )
        conn.commit()
        cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
        row = cursor.fetchone()
        user = dict(row)
    else:
        user = dict(row)
        # If user exists, check for reset or missing data
        needs_update = False
        
        # 1. Reset check count if new day or if last_check_date is None (new migration)
        if user.get('last_check_date') != today:
            user['daily_checks'] = 0
            user['last_check_date'] = today
            needs_update = True
        
        # 2. Update name/picture if we have them now (e.g. from Google login)
        if name and not user.get('name'):
            user['name'] = name
            needs_update = True
        if picture and not user.get('picture'):
            user['picture'] = picture
            needs_update = True
            
        if needs_update:
            cursor.execute(
                "UPDATE users SET daily_checks = ?, last_check_date = ?, name = ?, picture = ? WHERE email = ?",
                (user['daily_checks'], user['last_check_date'], user['name'], user['picture'], email)
            )
            conn.commit()
            
    conn.close()
    return user

def update_user_checks(email, count):
    """Update the number of checks performed by a user."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute(
        "UPDATE users SET daily_checks = ? WHERE email = ?",
        (count, email)
    )
    conn.commit()
    conn.close()

def create_user(email, password_hash, name=None, picture=None):
    """Insert a new user into the database manually (Email/Password)."""
    try:
        today = datetime.now().strftime("%Y-%m-%d")
        conn = get_db_connection()
        cursor = conn.cursor()
        cursor.execute(
            "INSERT INTO users (email, password_hash, name, picture, daily_checks, last_check_date) VALUES (?, ?, ?, ?, ?, ?)",
            (email, password_hash, name or email.split('@')[0], picture or "https://www.gravatar.com/avatar/00000000000000000000000000000000?d=mp&f=y", 0, today)
        )
        conn.commit()
        conn.close()
        return True
    except sqlite3.IntegrityError:
        return False

def get_user_by_email(email):
    """Retrieve a user by their email address."""
    conn = get_db_connection()
    cursor = conn.cursor()
    cursor.execute("SELECT * FROM users WHERE email = ?", (email,))
    user = cursor.fetchone()
    conn.close()
    return user

# Initialize the DB on import
init_db()
