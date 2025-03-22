import datetime
import sqlite3
import uuid
from db import get_db
from datetime import datetime

def initialize_db():
    """Ensure the database has the necessary fields."""
    conn = sqlite3.connect('users.db')
    cursor = conn.cursor()
    
    # Add new columns if they don't exist
    cursor.execute("""
        CREATE TABLE users (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            username TEXT UNIQUE NOT NULL,
            password TEXT NOT NULL,
            usertype TEXT NOT NULL,
            plan TEXT NOT NULL,
            daily_queries_intelx INTEGER NOT NULL,
            daily_queries_snusbase INTEGER NOT NULL,
            daily_emails INTEGER NOT NULL,
            api_key TEXT UNIQUE,
            time_of_signup TEXT,
            last_refresh TEXT,
            months_valid INTEGER
        )
    """)
    
    # Ensure all new columns exist
    columns_to_check = ["api_key", "time_of_signup", "last_refresh", "months_valid", "daily_queries_intelx","daily_queries_snusbase", "plan"]
    existing_columns = [row[1] for row in cursor.execute("PRAGMA table_info(users)")] 
    
    if "queries_left" in existing_columns:
        cursor.execute("ALTER TABLE users RENAME COLUMN queries_left TO daily_queries_left")
    
    for column in columns_to_check:
        if column not in existing_columns:
            if column == "api_key":
                cursor.execute("ALTER TABLE users ADD COLUMN api_key TEXT")
            elif column == "time_of_signup":
                cursor.execute("ALTER TABLE users ADD COLUMN time_of_signup TEXT")
            elif column == "last_refresh":
                cursor.execute("ALTER TABLE users ADD COLUMN last_refresh TEXT")
            elif column == "months_valid":
                cursor.execute("ALTER TABLE users ADD COLUMN months_valid INTEGER")
            elif column == "daily_queries_intelx":
                cursor.execute("ALTER TABLE users ADD COLUMN daily_queries_intelx INTEGER DEFAULT 0")
            elif column == "daily_queries_snusbase":
                cursor.execute("ALTER TABLE users ADD COLUMN daily_queries_snusbase INTEGER DEFAULT 0")
            elif column == "plan":
                cursor.execute("ALTER TABLE users ADD COLUMN plan TEXT NOT NULL DEFAULT 'free'")
    
    conn.commit()
    conn.close()

def generate_api_key():
    """Generate a unique API key."""
    return str(uuid.uuid4())

def get_default_data(plan):
    """Return the default daily queries for a given plan."""
    plan_defaults = {"free":{'intelx_queries':0, 'snusbase_queries':1, 'spam_emails':0,'cost': 0},
                     "basic": {'intelx_queries':10,'snusbase_queries':20,'spam_emails':100,'cost':50},
                     "premium": {'intelx_queries':40, 'snusbase_queries':60,'spam_emails':100, 'cost':150},
                     "lifetime":{'intelx_queries':100000, 'snusbase_queries':100000,'spam_emails':10000, 'cost':15000}}
    return plan_defaults.get(plan)

def modify_user(username, usertype=None, plan=None, months_valid=None, generate_new_api_key=False):
    """Modify an existing user without using a closed database connection."""
    conn = sqlite3.connect('users.db')  # Use a fresh connection
    cursor = conn.cursor()

    cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
    user = cursor.fetchone()

    if user:
        updates = []
        params = []
        if usertype:
            updates.append("usertype = ?")
            params.append(usertype)
        if plan:
            current_utc_time = datetime.utcnow().strftime("%Y-%m-%d %H:%M:%S")
            updates.append("last_refresh = ?")
            params.append(current_utc_time)
            updates.append("plan = ?")
            params.append(plan)
            updates.append("daily_queries_intelx = ?")
            params.append(get_default_data(plan)["intelx_queries"])
            updates.append("daily_queries_snusbase = ?")
            params.append(get_default_data(plan)["snusbase_queries"])
            updates.append("daily_emails =?")
            params.append(get_default_data(plan)["spam_emails"])
        if months_valid is not None:
            cursor.execute("SELECT months_valid FROM users WHERE username = ?", (username,))
            existing_months = cursor.fetchone()
            if existing_months and existing_months[0] > 0:
                months_valid += existing_months[0]
            updates.append("months_valid = ?")
            params.append(months_valid)
        if generate_new_api_key:
            new_api_key = generate_api_key()
            updates.append("api_key = ?")
            params.append(new_api_key)
            print(f"New API Key generated for {username}: {new_api_key}")
        if updates:
            params.append(username)
            cursor.execute(f"UPDATE users SET {', '.join(updates)} WHERE username = ?", params)
            conn.commit()
            print(f"User {username} updated successfully.")
        else:
            print("No updates provided.")
    else:
        print("User not found.")

    conn.close()  # Ensure the connection is closed


def check_and_decrement_queries(username, api_source, num_queries:int=None, conn=None):
    """Check if the user has queries left and decrement by 1 if available."""
    close_conn = False
    if conn is None:
        conn = get_db()
        close_conn = True  # Only close if we created the connection
    if api_source == "intelx":
        cursor = conn.cursor()
        cursor.execute("SELECT daily_queries_intelx FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result and result[0] > 0:
            new_count = result[0] - 1
            cursor.execute("UPDATE users SET daily_queries_intelx = ? WHERE username = ?", (new_count, username))
            conn.commit()
    elif api_source == "snusbase":
        cursor = conn.cursor()
        cursor.execute("SELECT daily_queries_snusbase FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result and result[0] > 0:
            new_count = result[0] - 1
            cursor.execute("UPDATE users SET daily_queries_snusbase = ? WHERE username = ?", (new_count, username))
            conn.commit()
    elif api_source == "email_bomb":
        cursor = conn.cursor()
        cursor.execute("SELECT daily_emails FROM users WHERE username = ?", (username,))
        result = cursor.fetchone()
        if result and result[0] > 0:
            new_count = result[0] - num_queries
            cursor.execute("UPDATE users SET daily_emails = ? WHERE username = ?",(new_count, username))
            conn.commit()

    if close_conn:
        conn.close()  # ✅ Only close if we created the connection

    return True if result and result[0] > 0 else False

def fetch_api_key(username):
    """Fetch the API key for a given username."""
    conn = get_db()
    cursor = conn.cursor()
    
    cursor.execute("SELECT api_key FROM users WHERE username = ?", (username,))
    result = cursor.fetchone()
    
    conn.close()
    
    if result:
        return result[0]
    else:
        print("User not found or API key not set.")
        return None
    

if __name__ == "__main__":
    modify_user("root", usertype="root", plan="lifetime", months_valid=100)
    #pass