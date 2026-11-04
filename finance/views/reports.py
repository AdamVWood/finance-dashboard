import csv
import datetime as dt
import io

from flask import Blueprint, Response, flash, render_template, request

from ..services import reports as reports_svc
from ..utils import cents_to_input, parse_date, today

bp = Blueprint("reports", __name__, url_prefix="/reports")


def _year():
    year = request.args.get("year", today().year, type=int)
    return year if 1990 <= year <= 2100 else today().year


def _range(year):
    start, end = dt.date(year, 1, 1), dt.date(year, 12, 31)
    try:
        if request.args.get("start"):
            start = parse_date(request.args["start"])
        if request.args.get("end"):
            end = parse_date(request.args["end"])
    except ValueError:
        flash("Invalid date in the category range - showing the whole year.", "error")
        start, end = dt.date(year, 1, 1), dt.date(year, 12, 31)
    if start > end:
        start, end = end, start
    return start, end


@bp.route("/")
def index():
    year = _year()
    monthly = reports_svc.monthly_series(12, start_month=dt.date(year, 1, 1))
    start, end = _range(year)
    categories = reports_svc.spending_by_category(start, end)
    income_categories = reports_svc.spending_by_category(start, end, kind="income")
    totals = reports_svc.income_expense(dt.date(year, 1, 1), dt.date(year, 12, 31))
    prev_totals = reports_svc.income_expense(dt.date(year - 1, 1, 1), dt.date(year - 1, 12, 31))
    elapsed_months = 12 if year < today().year else (today().month if year == today().year else 0)
    chart = {
        "monthly": [{"label": m["label"].split()[0], "income": m["income_cents"], "expenses": m["expense_cents"],
                     "net": m["net_cents"]} for m in monthly],
        "categories": [{"label": c["name"], "value": c["total"]}
                       for c in reports_svc.spending_by_category(start, end, top=8)["items"]],
        "savings_rate": [{"label": m["label"].split()[0], "value": m["savings_rate"]} for m in monthly],
    }
    return render_template(
        "reports/index.html",
        year=year,
        years=reports_svc.years_with_data(),
        monthly=monthly,
        totals=totals,
        prev_totals=prev_totals,
        averages={
            "income": totals["income_cents"] / elapsed_months if elapsed_months else 0,
            "expenses": totals["expense_cents"] / elapsed_months if elapsed_months else 0,
        },
        categories=categories,
        income_categories=income_categories,
        start=start,
        end=end,
        matrix=reports_svc.category_matrix(year),
        budget_lines=reports_svc.budget_vs_actual_year(year),
        chart=chart,
    )


@bp.route("/monthly.csv")
def monthly_csv():
    year = _year()
    monthly = reports_svc.monthly_series(12, start_month=dt.date(year, 1, 1))
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["month", "income", "expenses", "net", "savings_rate_pct"])
    for m in monthly:
        rate = "" if m["savings_rate"] is None else f"{m['savings_rate']:.1f}"
        writer.writerow([f"{m['year']}-{m['month']:02d}", cents_to_input(m["income_cents"]),
                         cents_to_input(m["expense_cents"]), cents_to_input(m["net_cents"]), rate])
    return Response(buffer.getvalue(), mimetype="text/csv",
                    headers={"Content-Disposition": f"attachment; filename=monthly-summary-{year}.csv"})


@bp.route("/categories.csv")
def categories_csv():
    year = _year()
    start, end = _range(year)
    data = reports_svc.spending_by_category(start, end)
    buffer = io.StringIO()
    writer = csv.writer(buffer)
    writer.writerow(["category", "total", "share_pct", "transactions"])
    for c in data["items"]:
        writer.writerow([c["name"], cents_to_input(c["total"]), f"{c['pct']:.1f}", c["count"]])
    name = f"spending-by-category-{start}-to-{end}.csv"
    return Response(buffer.getvalue(), mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={name}"})
