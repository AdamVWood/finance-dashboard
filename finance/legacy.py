"""Import data from the original (version 1) database, ``database/finance.db``.

Mapping from the old design:
  * Old transaction types: 'Deposit' -> income; 'Withdrawal', 'Direct Debit',
    'Fee', 'Remittance', 'Transfer' -> expense (the old app had no accounts,
    so true transfers can't be reconstructed). All go into one account,
    "Imported account".
  * Old categories had no income/expense type; each is created as the kind
    it was used with.
  * Savings goals keep their current amount as a single "Imported balance"
    contribution. Budgets and investments map field for field.
"""

import sqlite3

from .db import get_db
from .utils import to_cents, today

INCOME_TYPES = {"deposit", "income"}


def import_legacy(path):
    old = sqlite3.connect(f"file:{path}?mode=ro", uri=True)
    old.row_factory = sqlite3.Row
    db = get_db()
    counts = {"transactions": 0, "budgets": 0, "goals": 0, "investments": 0}
    try:
        tables = {r[0] for r in old.execute("SELECT name FROM sqlite_master WHERE type='table'")}
        old_cats = {r["id"]: r["name"] for r in old.execute("SELECT id, name FROM categories")} \
            if "categories" in tables else {}

        def category(old_id, kind):
            name = old_cats.get(old_id) or ("Other income" if kind == "income" else "Other expenses")
            row = db.execute("SELECT id FROM categories WHERE name = ? COLLATE NOCASE AND kind = ?",
                             (name, kind)).fetchone()
            if row:
                return row["id"]
            return db.execute("INSERT INTO categories (name, kind) VALUES (?, ?)", (name, kind)).lastrowid

        txns = list(old.execute("SELECT * FROM transactions")) if "transactions" in tables else []
        if txns:
            first = min(t["date"] for t in txns)
            acc = db.execute("SELECT id FROM accounts WHERE name = 'Imported account'").fetchone()
            account_id = acc["id"] if acc else db.execute(
                "INSERT INTO accounts (name, type, opened_on) VALUES ('Imported account', 'checking', ?)", (first,)
            ).lastrowid
            for t in txns:
                kind = "income" if (t["transaction_type"] or "").lower() in INCOME_TYPES else "expense"
                db.execute(
                    """INSERT INTO transactions (date, description, type, amount_cents, account_id, category_id, notes)
                       VALUES (?, ?, ?, ?, ?, ?, ?)""",
                    (t["date"], t["description"] or t["transaction_type"], kind, abs(to_cents(t["amount"])),
                     account_id, category(t["category_id"], kind), f"Imported (was '{t['transaction_type']}')"),
                )
                counts["transactions"] += 1

        if "budgets" in tables:
            for b in old.execute("SELECT * FROM budgets"):
                db.execute(
                    "INSERT OR IGNORE INTO budgets (category_id, year, month, amount_cents) VALUES (?, ?, ?, ?)",
                    (category(b["category_id"], "expense"), b["year"], b["month"], to_cents(b["amount"])),
                )
                counts["budgets"] += 1

        if "savings_goals" in tables:
            for g in old.execute("SELECT * FROM savings_goals"):
                start = (g["created_at"] or today().isoformat())[:10]
                gid = db.execute(
                    "INSERT INTO savings_goals (name, target_cents, start_date, deadline) VALUES (?, ?, ?, ?)",
                    (g["name"], to_cents(g["target_amount"]), start, g["deadline"] or None),
                ).lastrowid
                if g["current_amount"]:
                    db.execute(
                        "INSERT INTO goal_contributions (goal_id, date, amount_cents, note) VALUES (?, ?, ?, ?)",
                        (gid, start, to_cents(g["current_amount"]), "Imported balance"),
                    )
                counts["goals"] += 1

        if "investments" in tables:
            for i in old.execute("SELECT * FROM investments"):
                asset_type = (i["asset_type"] or "other").lower()
                if asset_type not in {"stock", "etf", "bond", "crypto"}:
                    asset_type = "other"
                hid = db.execute(
                    """INSERT INTO investments (name, ticker, asset_type, quantity, purchase_price, purchase_date)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (i["name"], i["ticker"], asset_type, i["quantity"], i["purchase_price"], i["purchase_date"]),
                ).lastrowid
                db.execute("INSERT INTO investment_prices (investment_id, date, price) VALUES (?, ?, ?)",
                           (hid, i["purchase_date"], i["purchase_price"]))
                counts["investments"] += 1
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        old.close()
    return counts
