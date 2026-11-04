"""Financial statistics used by the dashboard and the reports page.

Income and expenses only ever count transactions of type 'income' and
'expense'. Transfers move money between your own accounts, so they are never
counted as income or spending.
"""

import datetime as dt

from ..db import get_db
from ..utils import add_months, last_n_months, month_end, month_label, pct, today
from . import accounts as accounts_svc
from . import goals as goals_svc
from . import investments as investments_svc


def income_expense(start, end):
    row = get_db().execute(
        """SELECT COALESCE(SUM(CASE WHEN type='income' THEN amount_cents END), 0) AS income,
                  COALESCE(SUM(CASE WHEN type='expense' THEN amount_cents END), 0) AS expenses,
                  COUNT(CASE WHEN type <> 'transfer' THEN 1 END) AS count
           FROM transactions WHERE date BETWEEN ? AND ?""",
        (str(start), str(end)),
    ).fetchone()
    income, expenses = row["income"], row["expenses"]
    return {
        "income_cents": income,
        "expense_cents": expenses,
        "net_cents": income - expenses,
        "savings_rate": pct(income - expenses, income),
        "count": row["count"],
    }


def monthly_series(months=12, end=None, start_month=None):
    """Income, expenses and net per month. Months with no data are zero."""
    if start_month:
        periods = [(add_months(start_month, i).year, add_months(start_month, i).month) for i in range(months)]
    else:
        periods = last_n_months(months, end)
    first = dt.date(*periods[0], 1)
    last = month_end(dt.date(*periods[-1], 1))
    rows = get_db().execute(
        """SELECT substr(date, 1, 7) AS ym,
                  SUM(CASE WHEN type='income' THEN amount_cents ELSE 0 END) AS income,
                  SUM(CASE WHEN type='expense' THEN amount_cents ELSE 0 END) AS expenses
           FROM transactions WHERE date BETWEEN ? AND ? GROUP BY ym""",
        (first.isoformat(), last.isoformat()),
    )
    by_month = {r["ym"]: r for r in rows}
    series = []
    for year, month in periods:
        r = by_month.get(f"{year:04d}-{month:02d}")
        income = r["income"] if r else 0
        expenses = r["expenses"] if r else 0
        series.append({
            "year": year,
            "month": month,
            "label": month_label(year, month),
            "income_cents": income,
            "expense_cents": expenses,
            "net_cents": income - expenses,
            "savings_rate": pct(income - expenses, income),
        })
    return series


def spending_by_category(start, end, kind="expense", top=None):
    rows = get_db().execute(
        """SELECT c.id, c.name, c.color, SUM(t.amount_cents) AS total, COUNT(*) AS count
           FROM transactions t JOIN categories c ON c.id = t.category_id
           WHERE t.type = ? AND t.date BETWEEN ? AND ?
           GROUP BY c.id ORDER BY total DESC""",
        (kind, str(start), str(end)),
    )
    items = [dict(r) for r in rows]
    grand = sum(i["total"] for i in items)
    for i in items:
        i["pct"] = pct(i["total"], grand) or 0
    if top and len(items) > top:
        rest = items[top - 1:]
        items = items[: top - 1] + [{
            "id": None, "name": f"Other ({len(rest)} categories)", "color": None,
            "total": sum(i["total"] for i in rest), "count": sum(i["count"] for i in rest),
            "pct": sum(i["pct"] for i in rest),
        }]
    return {"items": items, "total_cents": grand}


def category_matrix(year):
    """Expense totals per category per month for one calendar year."""
    rows = get_db().execute(
        """SELECT c.id, c.name, CAST(substr(t.date, 6, 2) AS INTEGER) AS month, SUM(t.amount_cents) AS total
           FROM transactions t JOIN categories c ON c.id = t.category_id
           WHERE t.type = 'expense' AND substr(t.date, 1, 4) = ?
           GROUP BY c.id, month""",
        (f"{year:04d}",),
    )
    table = {}
    for r in rows:
        entry = table.setdefault(r["id"], {"name": r["name"], "months": [0] * 12, "total": 0})
        entry["months"][r["month"] - 1] = r["total"]
        entry["total"] += r["total"]
    lines = sorted(table.values(), key=lambda e: -e["total"])
    month_totals = [sum(line["months"][i] for line in lines) for i in range(12)]
    return {"lines": lines, "month_totals": month_totals, "total": sum(month_totals)}


def budget_vs_actual_year(year):
    rows = get_db().execute(
        """SELECT c.name,
                  COALESCE((SELECT SUM(b.amount_cents) FROM budgets b WHERE b.category_id = c.id AND b.year = :y), 0)
                      AS budget,
                  COALESCE((SELECT SUM(t.amount_cents) FROM transactions t
                            WHERE t.category_id = c.id AND t.type = 'expense'
                              AND substr(t.date, 1, 4) = :ys
                              AND CAST(substr(t.date, 6, 2) AS INTEGER) IN
                                  (SELECT month FROM budgets b2 WHERE b2.category_id = c.id AND b2.year = :y)), 0)
                      AS actual
           FROM categories c WHERE c.kind = 'expense'""",
        {"y": year, "ys": f"{year:04d}"},
    )
    lines = [dict(r) for r in rows if r["budget"]]
    for line in lines:
        line["diff"] = line["budget"] - line["actual"]
        line["used_pct"] = pct(line["actual"], line["budget"])
    return sorted(lines, key=lambda line: line["used_pct"] or 0, reverse=True)


def years_with_data():
    rows = get_db().execute("SELECT DISTINCT substr(date, 1, 4) AS y FROM transactions ORDER BY y DESC")
    years = [int(r["y"]) for r in rows]
    if today().year not in years:
        years.insert(0, today().year)
    return sorted(set(years), reverse=True)


# ---------------------------------------------------------------------------
# Net worth
# ---------------------------------------------------------------------------

def net_worth(as_of=None):
    as_of = as_of or today()
    acc = accounts_svc.totals(as_of.isoformat())
    invest = investments_svc.value_at(as_of.isoformat())
    assets = acc["cash_assets_cents"] + invest
    return {
        "cash_assets_cents": acc["cash_assets_cents"],
        "investments_cents": invest,
        "assets_cents": assets,
        "liabilities_cents": acc["liabilities_cents"],
        "net_worth_cents": assets - acc["liabilities_cents"],
    }


def net_worth_history(months=12, ref=None):
    """Net worth at the end of each of the last ``months`` months.

    Derived from opening balances, transactions and the investment price
    history, so it is available retroactively without any snapshots.
    """
    ref = ref or today()
    series = []
    for year, month in last_n_months(months, ref):
        point = min(month_end(dt.date(year, month, 1)), ref)
        worth = net_worth(point)
        series.append({
            "label": month_label(year, month),
            "date": point.isoformat(),
            "assets_cents": worth["assets_cents"],
            "liabilities_cents": worth["liabilities_cents"],
            "net_worth_cents": worth["net_worth_cents"],
        })
    return series


def dashboard_summary(period, start, end, prev_start=None, prev_end=None):
    current = income_expense(start, end)
    previous = income_expense(prev_start, prev_end) if prev_start else None
    worth = net_worth()
    worth_month_ago = net_worth(add_months(today(), -1))
    goals = goals_svc.totals()
    return {
        "period": period,
        "start": start,
        "end": end,
        "current": current,
        "previous": previous,
        "net_worth": worth,
        "net_worth_change_cents": worth["net_worth_cents"] - worth_month_ago["net_worth_cents"],
        "goals": goals,
    }
