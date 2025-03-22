import datetime
import os
import time
from flask import Flask, session, render_template, request, redirect, url_for, g
from flask_session import Session
from dotenv import load_dotenv
from threading import Thread
from search.routes import search_bp
from display.routes import display_bp
from display.snusbase_routes import snusbase_bp
from search.email_bomb import bomber_bp
from werkzeug.security import generate_password_hash, check_password_hash
from db import get_db  
from user_administration import generate_api_key, get_default_data


# Load environment variables
load_dotenv()
API_KEY = os.getenv("INTELX_API_KEY")
DOWNLOAD_FOLDER = os.getenv("DOWNLOAD_FOLDER", "downloads")

# Ensure the download folder exists
os.makedirs(DOWNLOAD_FOLDER, exist_ok=True)

app = Flask(__name__)
app.config["DOWNLOAD_FOLDER"] = DOWNLOAD_FOLDER
app.config["API_KEY"] = API_KEY
app.config["SESSION_TYPE"] = "filesystem"
app.config["DATABASE"] = "users.db"
Session(app)

# Register blueprints
app.register_blueprint(search_bp)
app.register_blueprint(display_bp)
app.register_blueprint(snusbase_bp)
app.register_blueprint(bomber_bp)


@app.before_request
def require_login():
    """Redirect users to login if they are not authenticated."""
    allowed_routes = ["login", "register", "static"]  # Allow access to login, register, and static files
    if "user" not in session and request.endpoint not in allowed_routes:
        return redirect(url_for("login"))

@app.route("/register", methods=["GET", "POST"])
def register():
    """Register a new user with hashed password and auto-assign plan, API key."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        hashed_password = generate_password_hash(password)

        # Default settings for new users
        plan = "free"  # Default plan
        months_valid = 1  # Default validity
        api_key = generate_api_key()  # Generate API key
        daily_queries_intelx = get_default_data(plan).get('intelx_queries')
        daily_queries_snusbase = get_default_data(plan).get('snusbase_queries')
        daily_emails = get_default_data(plan).get('spam_emails')  
        db = get_db()
        cursor = db.cursor()
        # Check if user exists
        cursor.execute("SELECT username FROM users WHERE username = ?", (username,))
        existing_user = cursor.fetchone()

        if existing_user:
             return render_template("register.html", error="Username already exists. Please choose a different one.")
        else:
            cursor.execute("""
                INSERT INTO users (
                    username, password, usertype, plan, 
                    daily_queries_intelx, daily_queries_snusbase, daily_emails, 
                    api_key, time_of_signup, last_refresh, months_valid
                ) 
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, datetime('now'), datetime('now'), ?)
            """, (
                username, hashed_password, "client", plan,
                daily_queries_intelx, daily_queries_snusbase, daily_emails,
                api_key, months_valid
            ))
            db.commit()
            print(f"User {username} registered with API Key: {api_key}")

        return redirect(url_for("login"))
    
    return render_template("register.html")


@app.route("/login", methods=["GET", "POST"])
def login():
    """Authenticate user using SQLite database and verify API Key."""
    if request.method == "POST":
        username = request.form.get("username")
        password = request.form.get("password")
        api_key = request.form.get("api_key")  

        db = get_db()
        cursor = db.cursor()
        cursor.execute("SELECT * FROM users WHERE username = ?", (username,))
        user = cursor.fetchone()

        if user and check_password_hash(user["password"], password):
            if user["api_key"] and user["api_key"] == api_key:  
                session["user"] = username
                session["daily_queries_intelx"] = user["daily_queries_intelx"]
                session["daily_queries_snusbase"] = user["daily_queries_snusbase"]
                session["months_valid"]=user["months_valid"]
                session["daily_emails"]=user["daily_emails"]
                session["api_key"] = api_key
                return redirect(url_for("search.dashboard"))
            else:
                return render_template("login.html", error="Invalid API Key")
        
        return render_template("login.html", error="Invalid username or password")

    return render_template("login.html")


@app.route("/logout")
def logout():
    session.pop("user", None)
    return redirect(url_for("login"))

@app.route("/")
def index():
    return redirect(url_for("login"))

@app.teardown_appcontext
def close_db_connection(exception=None):
    """Close the database connection after each request."""
    db = g.pop("db_connection", None)
    if db is not None:
        db.close()


def refresh_daily_queries():
    """Function to refresh daily queries for users."""
    while True:
        with app.app_context():  
            conn = get_db()
            cursor = conn.cursor()

            current_time = datetime.datetime.now(datetime.timezone.utc)
            cursor.execute("SELECT username, last_refresh, plan FROM users")
            users = cursor.fetchall()

            for username, last_refresh, plan in users:
                next_refresh = datetime.datetime.strptime(last_refresh, "%Y-%m-%d %H:%M:%S").replace(tzinfo=datetime.timezone.utc) + datetime.timedelta(days=1)
                if current_time >= next_refresh:
                    new_queries_intelx = get_default_data(plan).get('intelx_queries')
                    new_queries_snusbase = get_default_data(plan).get('snusbase_queries')
                    new_emails = get_default_data(plan).get('spam_emails')
                    cursor.execute(
                        "UPDATE users SET daily_queries_intelx = ?, daily_queries_snusbase = ?, daily_emails = ?, last_refresh = ? WHERE username = ?",
                        (new_queries_intelx, new_queries_snusbase, new_emails, current_time.strftime("%Y-%m-%d %H:%M:%S"), username),
                    )
                    conn.commit()
                    print(f"Daily queries refreshed for {username}")
            conn.close()
        time.sleep(60)  # Sleep for 60 seconds before checking again

if __name__ == "__main__":
    query_refresh_thread = Thread(target=refresh_daily_queries, daemon=True)
    query_refresh_thread.start()
    app.run(debug=True)


