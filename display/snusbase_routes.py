from flask import Blueprint, redirect, render_template, request, session, url_for
from user_administration import check_and_decrement_queries
from snusbase_api import search_snusbase
from db import get_db

snusbase_bp = Blueprint("snusbase", __name__)

@snusbase_bp.route("/snusbase_results", methods=["GET", "POST"])
def snusbase_results():
    """Handles displaying Snusbase search results."""
    if "user" not in session:
        return redirect(url_for("login"))

    conn = get_db()
    cursor = conn.cursor()
    cursor.execute("SELECT username, daily_queries_snusbase, months_valid FROM users WHERE username = ?", (session["user"],))
    user = cursor.fetchone()

    if not user:
        return redirect(url_for("login"))

    username = user["username"]
    queries_snusbase = user["daily_queries_snusbase"]
    months_valid = int(user["months_valid"])
    api = "snusbase"

    results = []
    column_headers = set()

    if request.method == "POST":
        query = request.form.get("query")
        snusbase_type = request.form.get("snusbase_type")

        if queries_snusbase > 0:
            try:
                print(query)
                print(snusbase_type)
                raw_results = search_snusbase(query, snusbase_type)  
                total_results = raw_results.get("total_results", {})

                for source, data in total_results.items():
                    formatted_data = {"source": source}  # Include source name
                    for key, value in data.items():
                        formatted_data[key] = value
                        column_headers.add(key)  # Collect unique field names dynamically

                    results.append(formatted_data)

                check_and_decrement_queries(username, api_source=api, conn=conn)  
                queries_snusbase -= 1

                print("✅ Column Headers Processed:", column_headers)  # Debugging Output
                print("✅ Snusbase Results Processed:", results)  # Debugging Output

            except Exception as e:
                print(f"Error occurred: {e}")
                return render_template("fallback.html")

    conn.close()

    return render_template("snusbase_results.html", results=results, username=username, queries_snusbase=queries_snusbase, column_headers=list(column_headers), months_left = months_valid)
