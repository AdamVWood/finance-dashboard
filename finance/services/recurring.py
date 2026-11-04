"""Recurring transactions (salary, rent, subscriptions, loan payments...).

A recurring item never changes balances by itself. When an occurrence falls
due, the app offers to "post" it, which creates a normal transaction and
moves the item on to its next date. Nothing is posted without the user
asking, so a cancelled subscription never silently creates spending.
"""

import datetime as dt

from ..db import get_db
from ..utils import ValidationError, add_months, cents_to_input, parse_date, today
from . import transactions as txn_svc

FREQUENCIES = {
    "weekly": "Weekly",
    "biweekly": "Every 2 weeks",
    "monthly": "Monthly",
    "quarterly": "Every 3 months",
    "yearly": "Yearly",
}
MAX_POST_PER_ITEM = 120  # safety net against posting years of history by accident


def occurrence(start, frequency, n):
    if frequency == "weekly":
        return start + dt.timedelta(weeks=n)
    if frequency == "biweekly":
        return start + dt.timedelta(weeks=2 * n)
    months = {"monthly": 1, "quarterly": 3, "yearly": 12}[frequency]
    return add_months(start, months * n)


def next_after(start, frequency, after):
    """First occurrence strictly after ``after``."""
    n = 0
    if frequency in ("monthly", "quarterly", "yearly"):
        step = {"monthly": 1, "quarterly": 3, "yearly": 12}[frequency]
        n = max(0, ((after.year - start.year) * 12 + after.month - start.month) // step - 1)
    elif after > start:
        n = max(0, (after - start).days // (7 if frequency == "weekly" else 14) - 1)
    while occurrence(start, frequency, n) <= after:
        n += 1
    return occurrence(start, frequency, n)


SELECT_SQL = """
    SELECT r.*, c.name AS category_name, a.name AS account_name, ta.name AS to_account_name
    FROM recurring r
    LEFT JOIN categories c ON c.id = r.category_id
    JOIN accounts a ON a.id = r.account_id
    LEFT JOIN accounts ta ON ta.id = r.to_account_id
"""


def _enrich(item, ref=None):
    ref = (ref or today()).isoformat()
    item["frequency_label"] = FREQUENCIES.get(item["frequency"], item["frequency"])
    item["finished"] = bool(item["end_date"] and item["next_date"] > item["end_date"])
    item["is_due"] = bool(item["is_active"] and not item["finished"] and item["next_date"] <= ref)
    return item


def list_items():
    rows = get_db().execute(SELECT_SQL + " ORDER BY r.is_active DESC, r.next_date, r.description COLLATE NOCASE")
    return [_enrich(dict(r)) for r in rows]


def get_item(item_id):
    row = get_db().execute(SELECT_SQL + " WHERE r.id = ?", (item_id,)).fetchone()
    return _enrich(dict(row)) if row else None


def _validate(form):
    v, data = txn_svc.validate(form)
    data["frequency"] = v.choice("frequency", "Frequency", FREQUENCIES)
    data["start_date"] = v.date("start_date", "First date")
    data["end_date"] = v.date("end_date", "End date", required=False)
    data["is_active"] = 0 if v.raw("is_paused") else 1
    if data["start_date"] and data["end_date"] and data["end_date"] < data["start_date"]:
        v.error("end_date", "The end date must be on or after the first date.")
    v.raise_if_errors()
    return data


INSERT_COLUMNS = (
    "description, type, amount_cents, account_id, to_account_id, category_id, frequency, "
    "start_date, next_date, end_date, is_active, notes"
)


def create_item(form):
    data = _validate(form)
    data["next_date"] = data["start_date"]
    db = get_db()
    cur = db.execute(
        f"""INSERT INTO recurring ({INSERT_COLUMNS})
            VALUES (:description, :type, :amount_cents, :account_id, :to_account_id, :category_id, :frequency,
                    :start_date, :next_date, :end_date, :is_active, :notes)""",
        data,
    )
    db.commit()
    return cur.lastrowid


def to_form(item):
    return {
        "type": item["type"],
        "amount": cents_to_input(item["amount_cents"]),
        "description": item["description"],
        "notes": item["notes"] or "",
        "account_id": str(item["account_id"]),
        "to_account_id": str(item["to_account_id"] or ""),
        "category_id": str(item["category_id"] or ""),
        "frequency": item["frequency"],
        "start_date": item["start_date"],
        "end_date": item["end_date"] or "",
        "is_paused": "" if item["is_active"] else "1",
    }


def update_item(item_id, form):
    existing = get_item(item_id)
    if not existing:
        raise ValidationError("Recurring item not found.")
    data = _validate(form)
    data["id"] = item_id
    start = parse_date(data["start_date"])
    if data["start_date"] != existing["start_date"] or data["frequency"] != existing["frequency"]:
        # Re-anchor the schedule: keep anything already posted, continue from the next new occurrence.
        last_posted = get_db().execute(
            "SELECT MAX(date) FROM transactions WHERE recurring_id = ?", (item_id,)
        ).fetchone()[0]
        if last_posted and last_posted >= data["start_date"]:
            data["next_date"] = next_after(start, data["frequency"], parse_date(last_posted)).isoformat()
        else:
            data["next_date"] = data["start_date"]
    else:
        data["next_date"] = existing["next_date"]
    db = get_db()
    db.execute(
        """UPDATE recurring SET description=:description, type=:type, amount_cents=:amount_cents,
               account_id=:account_id, to_account_id=:to_account_id, category_id=:category_id,
               frequency=:frequency, start_date=:start_date, next_date=:next_date, end_date=:end_date,
               is_active=:is_active, notes=:notes
           WHERE id=:id""",
        data,
    )
    db.commit()


def delete_item(item_id):
    db = get_db()
    if db.execute("DELETE FROM recurring WHERE id = ?", (item_id,)).rowcount == 0:
        raise ValidationError("Recurring item not found.")
    db.commit()


def due_occurrences(ref=None):
    """List of (item, date) pairs that are due on or before ``ref``."""
    ref = ref or today()
    due = []
    for item in list_items():
        if not item["is_due"]:
            continue
        start = parse_date(item["start_date"])
        current = parse_date(item["next_date"])
        end = parse_date(item["end_date"]) if item["end_date"] else None
        count = 0
        while current <= ref and (end is None or current <= end) and count < MAX_POST_PER_ITEM:
            due.append((item, current.isoformat()))
            current = next_after(start, item["frequency"], current)
            count += 1
    return due


def post_due(item_id=None, ref=None):
    """Create transactions for due occurrences. Returns how many were posted."""
    db = get_db()
    posted = 0
    advanced = {}
    for item, when in due_occurrences(ref):
        if item_id is not None and item["id"] != item_id:
            continue
        form = {**to_form(item), "date": when}
        txn_svc.create_transaction(form, recurring_id=item["id"], commit=False)
        advanced[item["id"]] = (item, when)
        posted += 1
    for item, last in advanced.values():
        nxt = next_after(parse_date(item["start_date"]), item["frequency"], parse_date(last))
        db.execute("UPDATE recurring SET next_date = ? WHERE id = ?", (nxt.isoformat(), item["id"]))
    db.commit()
    return posted


def skip_next(item_id):
    item = get_item(item_id)
    if not item:
        raise ValidationError("Recurring item not found.")
    nxt = next_after(parse_date(item["start_date"]), item["frequency"], parse_date(item["next_date"]))
    db = get_db()
    db.execute("UPDATE recurring SET next_date = ? WHERE id = ?", (nxt.isoformat(), item_id))
    db.commit()


def upcoming(days=30, ref=None):
    """Occurrences in the next ``days`` days (for the dashboard)."""
    ref = ref or today()
    horizon = ref + dt.timedelta(days=days)
    out = []
    for item in list_items():
        if not item["is_active"] or item["finished"]:
            continue
        start = parse_date(item["start_date"])
        current = parse_date(item["next_date"])
        end = parse_date(item["end_date"]) if item["end_date"] else None
        while current <= horizon and (end is None or current <= end):
            if current > ref:
                out.append({**item, "date": current.isoformat()})
            current = next_after(start, item["frequency"], current)
    return sorted(out, key=lambda x: x["date"])
