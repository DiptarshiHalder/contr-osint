import sqlite3
from flask import g, current_app

def get_db():
    """Ensure each request gets a fresh database connection."""
    if "db_connection" not in g:
        g.db_connection = sqlite3.connect(current_app.config["DATABASE"], timeout=10)
        g.db_connection.row_factory = sqlite3.Row
        g.db_connection.execute("PRAGMA journal_mode=WAL;")  # Enable WAL mode
    return g.db_connection

