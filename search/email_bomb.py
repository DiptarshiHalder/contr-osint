from flask import Blueprint, redirect, render_template, request, session, url_for
from email_bomb_api import send_email_bomb
from user_administration import check_and_decrement_queries
from db import get_db

bomber_bp = Blueprint("bomber",__name__)

@bomber_bp.route("/dashboard/payload", methods=["POST"])
def payload():
    if "user" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()  
    cursor = conn.cursor()
    cursor.execute("SELECT username, months_valid, daily_emails FROM users WHERE username = ?", (session["user"],))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return redirect(url_for("login"))
    
    username = user["username"]
    months_valid = int(user["months_valid"])
    emails_left = int(user["daily_emails"])
    if months_valid > 0:
        if request.method == "POST":
            try:
                email = request.form.get('email')
                email_count = request.form.get('mail_count')
                if not email or not email_count:
                    return redirect(url_for("bomber.dashboard"))
                if emails_left < email_count:
                    raise Exception
            except Exception as e:
                print(e)
            else:
                send_email_bomb(email, email_count)
            finally:
                check_and_decrement_queries(username=username, api_source="email_bomb", num_queries=email_count, conn=conn)               
    session["email"] = email
    session["email_count"] = email_count
    session["active_section"] = "email"

    return redirect(url_for("bomber.dashboard"))


@bomber_bp.route("/dashboard", methods=["GET"])
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))
    
    conn = get_db()  
    cursor = conn.cursor()
    cursor.execute("SELECT username, months_valid FROM users WHERE username = ?", (session["user"],))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return redirect(url_for("login"))
    
    username = user["username"]
    months_valid = int(user["months_valid"])
    session.pop("email", None)  # Retrieve and clear session data
    session.pop("email_count", None)
    active_section = session.pop("active_section", "osint-search")  # Default to search section

    return render_template('index.html', response = True, username=username, months_left = months_valid, active_section=active_section)