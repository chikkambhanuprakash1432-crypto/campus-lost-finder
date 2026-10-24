
from flask import (
    Flask, render_template, request,
    redirect, url_for, flash
)
import os
import secrets
import sqlite3
from pathlib import Path

app = Flask(__name__)
app.secret_key = os.environ.get("SECRET_KEY") or secrets.token_hex(32)

DATABASE = Path(__file__).with_name("database.db")


# Connect to the SQLite database
def get_db_connection():
    connection = sqlite3.connect(DATABASE)
    connection.row_factory = sqlite3.Row
    return connection


# Create the table if it does not already exist
def create_table():
    connection = get_db_connection()

    connection.execute("""
        CREATE TABLE IF NOT EXISTS items (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            item_type TEXT NOT NULL,
            item_name TEXT NOT NULL,
            category TEXT NOT NULL,
            location TEXT NOT NULL,
            description TEXT NOT NULL,
            contact TEXT NOT NULL,
            created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
        )
    """)

    connection.commit()
    connection.close()


# Home page: show and search reports

@app.route("/")
def home():
    search_query = request.args.get("q", "").strip()
    selected_category = request.args.get("category", "").strip()

    connection = get_db_connection()

    # Build search filters
    conditions = []
    values = []

    if search_query:
        conditions.append(
            "(item_name LIKE ? OR category LIKE ? OR location LIKE ?)"
        )
        keyword = f"%{search_query}%"
        values.extend([keyword, keyword, keyword])

    if selected_category:
        conditions.append("category = ?")
        values.append(selected_category)

    sql = "SELECT * FROM items"

    if conditions:
        sql += " WHERE " + " AND ".join(conditions)

    sql += " ORDER BY id DESC"

    items = connection.execute(sql, values).fetchall()

    # Count all reports for the dashboard
    stats = connection.execute("""
        SELECT
            COUNT(*) AS total,
            SUM(CASE WHEN item_type = 'Lost' THEN 1 ELSE 0 END) AS lost,
            SUM(CASE WHEN item_type = 'Found' THEN 1 ELSE 0 END) AS found
        FROM items
    """).fetchone()

    connection.close()

    return render_template(
        "index.html",
        items=items,
        search_query=search_query,
        selected_category=selected_category,
        stats=stats
    )
# Display the report form
@app.route("/report", methods=["GET"])
def report_form():
    selected_type = request.args.get("type", "Lost")

    if selected_type not in ("Lost", "Found"):
        selected_type = "Lost"

    return render_template(
        "report.html",
        selected_type=selected_type
    )


# Save the submitted report
@app.route("/report", methods=["POST"])
def save_report():
    item_type = request.form.get("item_type", "").strip()
    item_name = request.form.get("item_name", "").strip()
    category = request.form.get("category", "").strip()
    location = request.form.get("location", "").strip()
    description = request.form.get("description", "").strip()
    contact = request.form.get("contact", "").strip()

    if (
        item_type not in ("Lost", "Found")
        or not all([
            item_name, category, location,
            description, contact
        ])
    ):
        flash("Please complete all fields correctly.", "error")
        return redirect(url_for("report_form"))

    connection = get_db_connection()

    connection.execute("""
        INSERT INTO items (
            item_type, item_name, category,
            location, description, contact
        )
        VALUES (?, ?, ?, ?, ?, ?)
    """, (
        item_type, item_name, category,
        location, description, contact
    ))

    connection.commit()
    connection.close()

    flash("Your item report was saved successfully!", "success")
    return redirect(url_for("home"))


if __name__ == "__main__":
    create_table()
    app.run(debug=True)