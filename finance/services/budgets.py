"""Monthly budgets per expense category, and spending against them."""

import datetime as dt

from ..db import get_db
from ..utils import ValidationError, Validator, add_months, month_end, pct

NEAR_LIMIT_PCT = 80


def _status(budget_cents, spent_cents):
    if not budget_cents:
        return ("unbudgeted", "No budget") if spent_cents else ("none", "No budget")
    used = spent_cents / budget_cents * 100
    if used > 100:
        return "over", "Over budget"
    if used == 100:
        return "near", "Fully used"
    if used >= NEAR_LIMIT_PCT:
        return "near", "Near limit"
    return "ok", "On track"


def month_overview(year, month):
    """Budget vs actual for every active expense category in a month."""
    start = dt.date(year, month, 1)
    params = {"year": year, "month": month, "start": start.isoformat(), "end": month_end(start).isoformat()}
    rows = get_db().execute(
        """
        SELECT c.id AS category_id, c.name, c.color, c.is_archived,
               b.id AS budget_id, b.amount_cents AS budget_cents,
               COALESCE((SELECT SUM(t.amount_cents) FROM transactions t
                         WHERE t.category_id = c.id AND t.type = 'expense'
                           AND t.date BETWEEN :start AND :end), 0) AS spent_cents
        FROM categories c
        LEFT JOIN budgets b ON b.category_id = c.id AND b.year = :year AND b.month = :month
        WHERE c.kind = 'expense'
        ORDER BY (b.id IS NULL), c.name COLLATE NOCASE
        """,
        params,
    )
    lines = []
    for r in rows:
        line = dict(r)
        if line["is_archived"] and not line["budget_id"] and not line["spent_cents"]:
            continue
        budget = line["budget_cents"] or 0
        line["remaining_cents"] = budget - line["spent_cents"]
        line["used_pct"] = pct(line["spent_cents"], budget)
        line["status"], line["status_label"] = _status(budget, line["spent_cents"])
        lines.append(line)

    budgeted = [line for line in lines if line["budget_id"]]
    total_budget = sum(line["budget_cents"] for line in budgeted)
    spent_in_budgeted = sum(line["spent_cents"] for line in budgeted)
    unbudgeted = sum(line["spent_cents"] for line in lines if not line["budget_id"])
    return {
        "year": year,
        "month": month,
        "start": params["start"],
        "end": params["end"],
        "lines": lines,
        "total_budget_cents": total_budget,
        "spent_budgeted_cents": spent_in_budgeted,
        "unbudgeted_spent_cents": unbudgeted,
        "total_spent_cents": spent_in_budgeted + unbudgeted,
        "remaining_cents": total_budget - spent_in_budgeted,
        "used_pct": pct(spent_in_budgeted, total_budget),
        "over": [line for line in budgeted if line["status"] == "over"],
        "near": [line for line in budgeted if line["status"] == "near"],
        "has_budgets": bool(budgeted),
    }


def set_budget(form):
    """Create, change or (with an empty amount) remove one category's budget."""
    v = Validator(form)
    category_id = v.integer("category_id", "Category")
    year = v.integer("year", "Year", minimum=1990, maximum=2100)
    month = v.integer("month", "Month", minimum=1, maximum=12)
    amount = v.money("amount", "Budget", required=False, allow_zero=True)
    db = get_db()
    if category_id:
        cat = db.execute("SELECT kind FROM categories WHERE id = ?", (category_id,)).fetchone()
        if not cat:
            v.error("category_id", "Category not found.")
        elif cat["kind"] != "expense":
            v.error("category_id", "Budgets can only be set for expense categories.")
    v.raise_if_errors()
    if amount is None:
        db.execute(
            "DELETE FROM budgets WHERE category_id = ? AND year = ? AND month = ?", (category_id, year, month)
        )
    else:
        db.execute(
            """INSERT INTO budgets (category_id, year, month, amount_cents) VALUES (?, ?, ?, ?)
               ON CONFLICT (category_id, year, month) DO UPDATE SET amount_cents = excluded.amount_cents""",
            (category_id, year, month, amount),
        )
    db.commit()


def save_month(year, month, amounts):
    """Save many budgets at once. ``amounts`` maps category_id -> raw input."""
    errors = {}
    for category_id, raw in amounts.items():
        try:
            set_budget({"category_id": str(category_id), "year": str(year), "month": str(month), "amount": raw})
        except ValidationError as exc:
            errors[f"amount_{category_id}"] = next(iter(exc.errors.values()))
    if errors:
        raise ValidationError(errors)


def copy_from_previous(year, month, overwrite=False):
    """Copy last month's budgets into this month. Returns number copied."""
    prev = add_months(dt.date(year, month, 1), -1)
    db = get_db()
    conflict = "DO UPDATE SET amount_cents = excluded.amount_cents" if overwrite else "DO NOTHING"
    cur = db.execute(
        f"""INSERT INTO budgets (category_id, year, month, amount_cents)
            SELECT category_id, ?, ?, amount_cents FROM budgets WHERE year = ? AND month = ?
            ON CONFLICT (category_id, year, month) {conflict}""",
        (year, month, prev.year, prev.month),
    )
    db.commit()
    return cur.rowcount


def clear_month(year, month):
    db = get_db()
    count = db.execute("DELETE FROM budgets WHERE year = ? AND month = ?", (year, month)).rowcount
    db.commit()
    return count


def suggested_amounts(year, month, months_back=3):
    """Average monthly spend per category over the previous few months."""
    start = add_months(dt.date(year, month, 1), -months_back)
    end = add_months(dt.date(year, month, 1), -1)
    rows = get_db().execute(
        """SELECT category_id, SUM(amount_cents) AS total FROM transactions
           WHERE type = 'expense' AND date BETWEEN ? AND ? GROUP BY category_id""",
        (start.isoformat(), month_end(end).isoformat()),
    )
    return {r["category_id"]: round(r["total"] / months_back) for r in rows}
