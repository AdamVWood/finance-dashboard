"""Income, expense and transfer transactions, including search and CSV."""

import csv
import io

from ..db import get_db
from ..utils import PERIODS, ValidationError, Validator, cents_to_input, parse_date, parse_money, period_range
from . import accounts as accounts_svc
from . import categories as categories_svc

TYPES = {"expense": "Expense", "income": "Income", "transfer": "Transfer"}
SORTS = {
    "date_desc": "t.date DESC, t.id DESC",
    "date_asc": "t.date ASC, t.id ASC",
    "amount_desc": "t.amount_cents DESC, t.date DESC",
    "amount_asc": "t.amount_cents ASC, t.date DESC",
    "description": "t.description COLLATE NOCASE ASC, t.date DESC",
}
PAGE_SIZE = 50

SELECT_SQL = """
    SELECT t.*, c.name AS category_name, c.color AS category_color,
           a.name AS account_name, ta.name AS to_account_name
    FROM transactions t
    LEFT JOIN categories c ON c.id = t.category_id
    JOIN accounts a ON a.id = t.account_id
    LEFT JOIN accounts ta ON ta.id = t.to_account_id
"""


def validate(form):
    """Validate a transaction form. Shared with recurring items and CSV import."""
    v = Validator(form)
    txn_type = v.choice("type", "Type", TYPES)
    amount = v.money("amount")
    description = v.text("description", "Description", max_length=200)
    notes = v.text("notes", "Notes", required=False, max_length=1000)
    account_id = v.integer("account_id", "Account")
    account = accounts_svc.get_account(account_id) if account_id else None
    if account_id and not account:
        v.error("account_id", "Choose a valid account.")

    to_account_id = category_id = None
    if txn_type == "transfer":
        to_account_id = v.integer("to_account_id", "Destination account")
        if to_account_id and not accounts_svc.get_account(to_account_id):
            v.error("to_account_id", "Choose a valid destination account.")
        elif to_account_id and to_account_id == account_id:
            v.error("to_account_id", "Destination must be different from the source account.")
    elif txn_type:
        category_id = v.integer("category_id", "Category")
        category = categories_svc.get_category(category_id) if category_id else None
        if category_id and not category:
            v.error("category_id", "Choose a valid category.")
        elif category and category["kind"] != txn_type:
            v.error("category_id", f"Choose an {txn_type} category for an {txn_type}.")
    return v, {
        "type": txn_type,
        "amount_cents": amount,
        "description": description,
        "notes": notes,
        "account_id": account_id,
        "to_account_id": to_account_id,
        "category_id": category_id,
    }


def _validate_full(form):
    v, data = validate(form)
    data["date"] = v.date("date")
    v.raise_if_errors()
    return data


def create_transaction(form, recurring_id=None, commit=True):
    data = _validate_full(form)
    data["recurring_id"] = recurring_id
    db = get_db()
    cur = db.execute(
        """INSERT INTO transactions (date, description, type, amount_cents, account_id, to_account_id,
                                     category_id, notes, recurring_id)
           VALUES (:date, :description, :type, :amount_cents, :account_id, :to_account_id,
                   :category_id, :notes, :recurring_id)""",
        data,
    )
    if commit:
        db.commit()
    return cur.lastrowid


def get_transaction(txn_id):
    row = get_db().execute(SELECT_SQL + " WHERE t.id = ?", (txn_id,)).fetchone()
    return dict(row) if row else None


def to_form(txn):
    """Convert a stored transaction into form field values for editing."""
    return {
        "type": txn["type"],
        "amount": cents_to_input(txn["amount_cents"]),
        "description": txn["description"],
        "notes": txn["notes"] or "",
        "account_id": str(txn["account_id"]),
        "to_account_id": str(txn["to_account_id"] or ""),
        "category_id": str(txn["category_id"] or ""),
        "date": txn["date"],
    }


def update_transaction(txn_id, form):
    if not get_transaction(txn_id):
        raise ValidationError("Transaction not found.")
    data = _validate_full(form)
    data["id"] = txn_id
    db = get_db()
    db.execute(
        """UPDATE transactions SET date=:date, description=:description, type=:type,
               amount_cents=:amount_cents, account_id=:account_id, to_account_id=:to_account_id,
               category_id=:category_id, notes=:notes, updated_at=CURRENT_TIMESTAMP
           WHERE id=:id""",
        data,
    )
    db.commit()


def delete_transaction(txn_id):
    db = get_db()
    if db.execute("DELETE FROM transactions WHERE id = ?", (txn_id,)).rowcount == 0:
        raise ValidationError("Transaction not found.")
    db.commit()


def delete_many(ids):
    ids = [int(i) for i in ids if str(i).isdigit()]
    if not ids:
        return 0
    db = get_db()
    marks = ",".join("?" * len(ids))
    count = db.execute(f"DELETE FROM transactions WHERE id IN ({marks})", ids).rowcount
    db.commit()
    return count


# ---------------------------------------------------------------------------
# Search
# ---------------------------------------------------------------------------

def parse_filters(args):
    """Turn query-string arguments into a clean filter dict plus any errors."""
    f = {
        "q": (args.get("q") or "").strip(),
        "type": args.get("type") if args.get("type") in TYPES else "",
        "category_id": args.get("category_id") if (args.get("category_id") or "").isdigit() else "",
        "account_id": args.get("account_id") if (args.get("account_id") or "").isdigit() else "",
        "period": args.get("period") if args.get("period") in PERIODS else "",
        "start": "",
        "end": "",
        "min": (args.get("min") or "").strip(),
        "max": (args.get("max") or "").strip(),
        "sort": args.get("sort") if args.get("sort") in SORTS else "date_desc",
    }
    errors = []
    for key in ("start", "end"):
        raw = (args.get(key) or "").strip()
        if raw:
            try:
                f[key] = parse_date(raw).isoformat()
            except ValueError:
                errors.append(f"'{raw}' is not a valid date.")
    if f["period"] and not (f["start"] or f["end"]):
        start, end = period_range(f["period"])
        f["start"], f["end"] = start.isoformat(), end.isoformat()
    if f["start"] and f["end"] and f["start"] > f["end"]:
        errors.append("The start date is after the end date.")
    for key in ("min", "max"):
        if f[key]:
            try:
                parse_money(f[key])
            except ValueError:
                errors.append(f"'{f[key]}' is not a valid amount.")
                f[key] = ""
    return f, errors


def _where(f):
    clauses, params = [], {}
    if f.get("q"):
        clauses.append(
            "(t.description LIKE :q ESCAPE '\\' OR t.notes LIKE :q ESCAPE '\\' OR c.name LIKE :q ESCAPE '\\')"
        )
        escaped = f["q"].replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
        params["q"] = f"%{escaped}%"
    if f.get("type"):
        clauses.append("t.type = :type")
        params["type"] = f["type"]
    if f.get("category_id"):
        clauses.append("t.category_id = :category_id")
        params["category_id"] = int(f["category_id"])
    if f.get("account_id"):
        clauses.append("(t.account_id = :account_id OR t.to_account_id = :account_id)")
        params["account_id"] = int(f["account_id"])
    if f.get("start"):
        clauses.append("t.date >= :start")
        params["start"] = f["start"]
    if f.get("end"):
        clauses.append("t.date <= :end")
        params["end"] = f["end"]
    if f.get("min"):
        clauses.append("t.amount_cents >= :min")
        params["min"] = parse_money(f["min"])
    if f.get("max"):
        clauses.append("t.amount_cents <= :max")
        params["max"] = parse_money(f["max"])
    return (" WHERE " + " AND ".join(clauses)) if clauses else "", params


def search(f, page=1, page_size=PAGE_SIZE):
    """Return matching transactions (one page), count and income/expense totals."""
    db = get_db()
    where, params = _where(f)
    summary = db.execute(
        f"""SELECT COUNT(*) AS count,
                   COALESCE(SUM(CASE WHEN t.type='income' THEN t.amount_cents END), 0) AS income,
                   COALESCE(SUM(CASE WHEN t.type='expense' THEN t.amount_cents END), 0) AS expenses
            FROM transactions t LEFT JOIN categories c ON c.id = t.category_id {where}""",
        params,
    ).fetchone()
    pages = max(1, -(-summary["count"] // page_size))
    page = min(max(1, page), pages)
    rows = db.execute(
        SELECT_SQL + where + f" ORDER BY {SORTS[f.get('sort') or 'date_desc']} LIMIT :limit OFFSET :offset",
        {**params, "limit": page_size, "offset": (page - 1) * page_size},
    )
    return {
        "rows": [dict(r) for r in rows],
        "count": summary["count"],
        "income_cents": summary["income"],
        "expense_cents": summary["expenses"],
        "page": page,
        "pages": pages,
    }


def recent(limit=8):
    return [dict(r) for r in get_db().execute(SELECT_SQL + " ORDER BY t.date DESC, t.id DESC LIMIT ?", (limit,))]


# ---------------------------------------------------------------------------
# CSV export / import
# ---------------------------------------------------------------------------

CSV_COLUMNS = ["date", "description", "type", "amount", "category", "account", "to_account", "notes"]


def export_csv(f):
    where, params = _where(f)
    rows = get_db().execute(SELECT_SQL + where + " ORDER BY t.date, t.id", params)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(CSV_COLUMNS)
    for r in rows:
        writer.writerow([
            r["date"], r["description"], r["type"], cents_to_input(r["amount_cents"]),
            r["category_name"] or "", r["account_name"], r["to_account_name"] or "", r["notes"] or "",
        ])
    return buffer.getvalue()


def import_csv(text, default_account_id=None, create_categories=True):
    """Import transactions from CSV text. All-or-nothing.

    Required columns: date, description, amount. Optional: type, category,
    account, to_account, notes. If ``type`` is missing, a negative amount is an
    expense and a positive amount is income. Returns the number imported or
    raises ValidationError with a list of row problems.
    """
    try:
        reader = csv.DictReader(io.StringIO(text.lstrip("﻿")))
        headers = [h.strip().lower() for h in (reader.fieldnames or [])]
    except csv.Error as exc:
        raise ValidationError(f"Could not read the CSV file: {exc}") from None
    missing = {"date", "description", "amount"} - set(headers)
    if missing:
        raise ValidationError(
            f"The CSV is missing required column(s): {', '.join(sorted(missing))}. "
            f"Expected columns: {', '.join(CSV_COLUMNS)}."
        )
    reader.fieldnames = headers

    db = get_db()
    problems, prepared = [], []
    for line_no, raw in enumerate(reader, start=2):
        row = {k: (v or "").strip() for k, v in raw.items() if k}
        if not any(row.values()):
            continue
        try:
            cents = parse_money(row.get("amount", ""))
        except ValueError as exc:
            problems.append(f"Row {line_no}: amount {exc}.")
            continue
        txn_type = (row.get("type") or "").lower()
        if txn_type in ("deposit", "credit"):
            txn_type = "income"
        elif txn_type in ("withdrawal", "debit", "payment"):
            txn_type = "expense"
        if not txn_type:
            txn_type = "expense" if cents < 0 else "income"
        form = {
            "date": row.get("date", ""),
            "description": row.get("description", ""),
            "type": txn_type,
            "amount": cents_to_input(abs(cents)),
            "notes": row.get("notes", ""),
        }
        try:
            form["date"] = parse_date(form["date"]).isoformat()
        except ValueError:
            pass  # validation below reports it

        account_name = row.get("account", "")
        if account_name:
            acc = accounts_svc.find_by_name(account_name)
            if not acc:
                problems.append(f"Row {line_no}: account '{account_name}' doesn't exist.")
                continue
            form["account_id"] = str(acc["id"])
        elif default_account_id:
            form["account_id"] = str(default_account_id)
        if txn_type == "transfer":
            dest = accounts_svc.find_by_name(row.get("to_account", ""))
            if dest:
                form["to_account_id"] = str(dest["id"])
        elif txn_type in TYPES:
            cat_name = row.get("category") or ("Other income" if txn_type == "income" else "Other expenses")
            cat = categories_svc.find_by_name(cat_name, txn_type)
            if cat:
                form["category_id"] = str(cat["id"])
            elif create_categories:
                form["category_id"] = str(categories_svc.get_or_create(cat_name, txn_type))
            else:
                problems.append(f"Row {line_no}: category '{cat_name}' doesn't exist.")
                continue
        v, data = validate(form)
        data["date"] = v.date("date")
        if v.errors:
            problems.append(f"Row {line_no}: " + " ".join(v.errors.values()))
            continue
        prepared.append(data)

    if problems:
        db.rollback()  # discard any categories created above
        raise ValidationError({"_form": "Nothing was imported. Fix these rows and try again.", "rows": problems})
    if not prepared:
        db.rollback()
        raise ValidationError("The CSV file contains no transactions.")
    db.executemany(
        """INSERT INTO transactions (date, description, type, amount_cents, account_id, to_account_id,
                                     category_id, notes)
           VALUES (:date, :description, :type, :amount_cents, :account_id, :to_account_id,
                   :category_id, :notes)""",
        prepared,
    )
    db.commit()
    return len(prepared)
