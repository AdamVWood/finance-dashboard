"""App settings, backups and full data reset."""

import datetime as dt
import sqlite3
import tempfile
from pathlib import Path

from flask import current_app

from ..db import connect, get_db, init_schema, is_valid_database_file
from ..utils import ValidationError, Validator

CURRENCIES = {
    "BBD": "$", "USD": "$", "CAD": "$", "TTD": "$", "JMD": "$", "XCD": "$", "GYD": "$",
    "GBP": "£", "EUR": "€", "AUD": "$", "NZD": "$", "INR": "₹", "JPY": "¥",
}


def get_all():
    return {r["key"]: r["value"] for r in get_db().execute("SELECT key, value FROM settings")}


def save(form):
    v = Validator(form)
    code = v.choice("currency_code", "Currency", CURRENCIES)
    symbol = v.text("currency_symbol", "Currency symbol", required=False, max_length=4)
    owner = v.text("owner_name", "Your name", required=False, max_length=60)
    v.raise_if_errors()
    db = get_db()
    values = {"currency_code": code, "currency_symbol": symbol or CURRENCIES[code], "owner_name": owner or ""}
    for key, value in values.items():
        db.execute(
            "INSERT INTO settings (key, value) VALUES (?, ?) ON CONFLICT (key) DO UPDATE SET value = excluded.value",
            (key, value),
        )
    db.commit()


def backup_to(path):
    """Write a consistent copy of the live database to ``path``."""
    dest = sqlite3.connect(path)
    try:
        get_db().backup(dest)
    finally:
        dest.close()
    return path


def backup_filename():
    return f"finance-backup-{dt.datetime.now():%Y%m%d-%H%M%S}.db"


def make_backup_file():
    tmp = Path(tempfile.mkdtemp()) / backup_filename()
    return backup_to(tmp)


def restore_from(upload_path):
    """Replace all data with the contents of an uploaded backup file."""
    if not is_valid_database_file(upload_path):
        raise ValidationError("That file isn't a valid backup from this app.")
    # Keep a safety copy of the current data before overwriting it.
    backup_dir = Path(current_app.config["BACKUP_DIR"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_to(backup_dir / f"before-restore-{dt.datetime.now():%Y%m%d-%H%M%S}.db")

    src = connect(upload_path)
    try:
        init_schema(src)  # bring older backups up to the current schema
        db = get_db()
        src.backup(db)
    finally:
        src.close()


def reset_all():
    """Delete every record (a safety backup is written first)."""
    backup_dir = Path(current_app.config["BACKUP_DIR"])
    backup_dir.mkdir(parents=True, exist_ok=True)
    backup_to(backup_dir / f"before-reset-{dt.datetime.now():%Y%m%d-%H%M%S}.db")
    db = get_db()
    for table in (
        "investment_prices", "investments", "goal_contributions", "savings_goals", "budgets",
        "transactions", "recurring", "accounts", "categories",
    ):
        db.execute(f"DELETE FROM {table}")
    init_schema(db)  # re-seeds the default categories


def has_any_data():
    db = get_db()
    return bool(db.execute(
        "SELECT (SELECT COUNT(*) FROM accounts) + (SELECT COUNT(*) FROM investments)"
        " + (SELECT COUNT(*) FROM savings_goals)"
    ).fetchone()[0])


def list_safety_backups():
    backup_dir = Path(current_app.config["BACKUP_DIR"])
    if not backup_dir.exists():
        return []
    files = sorted(backup_dir.glob("*.db"), reverse=True)
    return [{"name": f.name, "size_kb": round(f.stat().st_size / 1024)} for f in files[:10]]

