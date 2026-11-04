"""Database connection handling, schema creation and migrations.

One SQLite connection is opened per request (stored on ``flask.g``) and closed
automatically when the request ends. Services receive the connection through
``get_db()`` so they never manage connections themselves.
"""

import sqlite3
from pathlib import Path

from flask import current_app, g

SCHEMA_VERSION = 1
SCHEMA_PATH = Path(__file__).with_name("schema.sql")

DEFAULT_CATEGORIES = {
    "income": [
        ("Salary", "#1baf7a"),
        ("Freelance & side income", "#2a78d6"),
        ("Interest & dividends", "#6250d6"),
        ("Gifts received", "#e87ba4"),
        ("Other income", "#8a8984"),
    ],
    "expense": [
        ("Housing & rent", "#2a78d6"),
        ("Groceries", "#1baf7a"),
        ("Dining out", "#eb6834"),
        ("Utilities", "#eda100"),
        ("Transportation", "#6250d6"),
        ("Phone & internet", "#e87ba4"),
        ("Health & medical", "#e34948"),
        ("Insurance", "#008300"),
        ("Education", "#256abf"),
        ("Entertainment", "#d55181"),
        ("Shopping", "#c98500"),
        ("Personal care", "#199e70"),
        ("Gifts & donations", "#9085e9"),
        ("Bank fees & charges", "#52514e"),
        ("Other expenses", "#8a8984"),
    ],
}

DEFAULT_SETTINGS = {
    "currency_code": "BBD",
    "currency_symbol": "$",
    "owner_name": "",
}


def connect(path):
    conn = sqlite3.connect(path, detect_types=0)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    conn.execute("PRAGMA busy_timeout = 5000")
    return conn


def get_db():
    if "db" not in g:
        g.db = connect(current_app.config["DATABASE"])
    return g.db


def close_db(_exc=None):
    db = g.pop("db", None)
    if db is not None:
        db.close()


def init_schema(conn):
    """Create tables if needed and apply migrations. Safe to run repeatedly."""
    conn.executescript(SCHEMA_PATH.read_text(encoding="utf-8"))
    version = conn.execute("PRAGMA user_version").fetchone()[0]
    if version < SCHEMA_VERSION:
        # Future migrations go here, e.g.:
        # if version < 2: conn.execute("ALTER TABLE ...")
        conn.execute(f"PRAGMA user_version = {SCHEMA_VERSION}")
    for key, value in DEFAULT_SETTINGS.items():
        conn.execute("INSERT OR IGNORE INTO settings (key, value) VALUES (?, ?)", (key, value))
    if conn.execute("SELECT COUNT(*) FROM categories").fetchone()[0] == 0:
        seed_default_categories(conn)
    conn.commit()


def seed_default_categories(conn):
    for kind, items in DEFAULT_CATEGORIES.items():
        for name, color in items:
            conn.execute(
                "INSERT OR IGNORE INTO categories (name, kind, color) VALUES (?, ?, ?)",
                (name, kind, color),
            )


def is_valid_database_file(path):
    """Return True if ``path`` looks like a database created by this app."""
    try:
        conn = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
        try:
            tables = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
            integrity = conn.execute("PRAGMA integrity_check").fetchone()[0]
        finally:
            conn.close()
    except sqlite3.DatabaseError:
        return False
    required = {"accounts", "transactions", "categories", "budgets", "savings_goals", "investments"}
    return integrity == "ok" and required.issubset(tables)


def init_app(app):
    app.teardown_appcontext(close_db)
    Path(app.config["DATABASE"]).parent.mkdir(parents=True, exist_ok=True)
    conn = connect(app.config["DATABASE"])
    try:
        init_schema(conn)
    finally:
        conn.close()
