from datetime import datetime, timezone, timedelta
from flask import Blueprint, redirect, render_template, request, session, current_app, send_file, url_for
import urllib.parse
from intelxapi import intelx
from db import get_db
from snusbase_api import search_snusbase
from user_administration import check_and_decrement_queries

search_bp = Blueprint("search", __name__)

def search_intelx(query):
    """Send a query to IntelX and fetch structured results."""
    with current_app.app_context():
        intelx_client = intelx(current_app.config["API_KEY"])

    response = intelx_client.search(query, maxresults=100)
    results = []
    if response and "records" in response:
        for record in response["records"]:
            systemid = record.get("systemid")
            filename = record.get("name", "Unknown_File").replace("/", "_")
            if systemid:
                results.append({
                    "systemid": systemid,
                    "title": filename,
                    "url": f"/view/{systemid}/{urllib.parse.quote(filename)}"
                })
    return results

@search_bp.route("/dashboard", methods=["GET", "POST"])
def dashboard():
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()  
    cursor = conn.cursor()
    cursor.execute("SELECT username, daily_emails, daily_queries_intelx, daily_queries_snusbase, months_valid, last_refresh FROM users WHERE username = ?", (session["user"],))
    user = cursor.fetchone()

    if not user:
        conn.close()
        return redirect(url_for("login"))

    username = user["username"]
    queries_intelx = user["daily_queries_intelx"]
    queries_snusbase = user["daily_queries_snusbase"]
    daily_emails = user["daily_emails"]
    months_valid = int(user["months_valid"])

     # Convert last_refresh to UTC timestamp
    last_refresh = datetime.strptime(user["last_refresh"], "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
    refresh_time = last_refresh + timedelta(hours=24)  # Next refresh time
    refresh_timestamp = int(refresh_time.timestamp()) 

    results = []
    column_headers = set()

    if request.method == "POST":
        if months_valid > 0:
            query = request.form.get("query")
            api_source = request.form.get("api_source")
            snusbase_type = request.form.get("snusbase_type") if api_source == "snusbase" else None

            try:
                if api_source == "snusbase":
                    if queries_snusbase > 0:
                        raw_results = search_snusbase(query, snusbase_type)
                        total_results = raw_results.get("total_results", {})

                        for source, data in total_results.items():
                            formatted_data = {"source": source}
                            for key, value in data.items():
                                formatted_data[key] = value
                                column_headers.add(key)
                            results.append(formatted_data)
                    check_and_decrement_queries(username, api_source=api_source, conn=conn)  
                    queries_snusbase -= 1
                elif api_source == "intelx":
                    if queries_intelx > 0: 
                        results = search_intelx(query)
                        check_and_decrement_queries(username, api_source=api_source, conn=conn)  
                        queries_intelx -= 1
            except Exception as e:
                print(f"Error occurred: {e}")
                conn.close()
                return render_template("fallback.html")

            conn.close()
            return render_template("index.html", results=results, username=username, queries_intelx=queries_intelx, queries_snusbase=queries_snusbase, api_source=api_source, column_headers=column_headers, refresh_timestamp=refresh_timestamp, months_left = months_valid, daily_emails=daily_emails)
        else:
            conn.close()
            return render_template("index.html", username=username, queries_intelx=queries_intelx, queries_snusbase=queries_snusbase,daily_emails=daily_emails, error="Subscription Over, Contact Support Team for renewal")
   
    conn.close()
    return render_template("index.html", username=username, queries_intelx=queries_intelx, queries_snusbase=queries_snusbase, refresh_timestamp=refresh_timestamp, months_left = months_valid,daily_emails=daily_emails)




    
