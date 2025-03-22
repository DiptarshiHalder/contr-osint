import os
import urllib.parse
import re
from flask import Blueprint, render_template, abort, current_app, session, request, send_file
from intelxapi import intelx
from db import get_db
from snusbase_api import search_snusbase
from user_administration import check_and_decrement_queries

display_bp = Blueprint("display", __name__)

def fetch_result(systemid, filename):
    """Fetch the result from IntelX API and save it as a file."""
    try:
        with current_app.app_context():
            intelx_client = intelx(current_app.config["API_KEY"])  # FIXED API Usage

        response = intelx_client.search(term=systemid, maxresults=1)
        if not response or "records" not in response:
            print("Error: No records found.")
            return None

        record = response["records"][0]
        sid = record.get("storageid")
        bucket = record.get("bucket")
        ctype = record.get("type")
        mediatype = record.get("media")

        if not all([sid, bucket, ctype, mediatype]):
            print("Error: Missing required fields.")
            return None
        file_view = intelx_client.GET_CAPABILITIES().get('paths').get('/file/view').get('Credit')
        file_preview = intelx_client.GET_CAPABILITIES().get('paths').get('/file/preview').get('Credit')
        # Fetch file content
        if file_preview > 0:
            file_content = intelx_client.FILE_PREVIEW(format=0, ctype=ctype, mediatype=mediatype, sid=sid, bucket=bucket,lines=1000000000)
        elif file_view > 0:
            file_content = intelx_client.FILE_VIEW(ctype=ctype, mediatype=mediatype, sid=sid, bucket=bucket)

        if not file_content:
            print("Error: No file content received.")
            return None

        # Ensure download folder exists
        download_folder = current_app.config["DOWNLOAD_FOLDER"]
        os.makedirs(download_folder, exist_ok=True)

        # Sanitize filename
        sanitized_filename = filename.replace("/", "_").replace("%20", "_")
        file_path = os.path.join(download_folder, sanitized_filename)

        # Save file
        with open(file_path, "w", encoding="utf-8", errors="ignore") as f:
            f.write(file_content)

        return file_path

    except Exception as e:
        print(f"Error fetching result: {e}")
        return None


@display_bp.route("/dashboard/search", methods=["GET", "POST"])
def search():
    """Handle search query and store it in session."""
    db = get_db()
    cursor = db.cursor()
    cursor.execute("SELECT username, daily_queries_intelx FROM users WHERE username = ?", (session["user"],))
    user = cursor.fetchone()
    username = user["username"]
    queries_left = user["daily_queries_intelx"]

    if request.method == "POST":
        user_query = request.form.get("query")
        api_source = request.form.get("api_source")  # Determine if user selected IntelX or Snusbase

        # Store query in session
        session["last_query"] = user_query

        if api_source == "snusbase":
            snusbase_type = request.form.get("snusbase_type")
            results = []
            column_headers = set()

            try:
                raw_results = search_snusbase(user_query, snusbase_type)
                total_results = raw_results.get("total_results", {})

                for source, data in total_results.items():
                    formatted_data = {"source": source}  
                    for key, value in data.items():
                        formatted_data[key] = value
                        column_headers.add(key)

                    results.append(formatted_data)

                return render_template("snusbase_results.html", results=results, username=username, queries_left=queries_left, column_headers=list(column_headers))

            except Exception as e:
                print(f"Error occurred during Snusbase search: {e}")
                return render_template("fallback.html")

        # If IntelX is selected, return `index.html`
        return render_template("index.html", query=user_query, username=username, queries_left=queries_left)

    return render_template("index.html", username=username, queries_left=queries_left)



@display_bp.route("/view/<systemid>/<filename>")
def view_file(systemid, filename):
    """Check if the file exists and render it in the browser."""
    decoded_filename = urllib.parse.unquote(filename)  # Fix encoding
    download_folder = current_app.config["DOWNLOAD_FOLDER"]
    file_path = os.path.join(download_folder, decoded_filename)

    if not os.path.exists(file_path):
        file_path = fetch_result(systemid, decoded_filename)

    if file_path and os.path.exists(file_path):
        with open(file_path, "r", encoding="utf-8", errors="ignore") as f:
            content = f.read()

        # Retrieve user query
        user_query = session.get("last_query", "")

        # Find first match and highlight all occurrences
        match = None
        if user_query:
            lines = content.splitlines()
            for line in lines:
                if user_query.lower() in line.lower():
                    match = line.replace(user_query, f"<span class='highlight'>{user_query}</span>")
                    break

            highlighted_content = re.sub(
                fr"({re.escape(user_query)})",
                r'<span class="highlight">\1</span>',
                content,
                flags=re.IGNORECASE
            )
            content = highlighted_content

        return render_template("result.html", content=content, match=match, file_path=decoded_filename, systemid=systemid)

    abort(404, description="File not found.")


@display_bp.route("/download/<systemid>/<filename>")
def download_file(systemid, filename):
    """Allow user to download the file with proper error handling."""
    decoded_filename = urllib.parse.unquote(filename)
    download_folder = current_app.config["DOWNLOAD_FOLDER"]
    file_path = os.path.join(download_folder, decoded_filename)

    if not os.path.exists(file_path):
        # Fetch file if it doesn't exist
        file_path = fetch_result(systemid, decoded_filename)

    if file_path and os.path.exists(file_path):
        try:
            return send_file(file_path, as_attachment=True)
        except Exception as e:
            abort(500, description=f"Error serving file: {str(e)}")

    abort(404, description="File not found.")
