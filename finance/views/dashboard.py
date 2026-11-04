from flask import Blueprint, render_template, request

from ..services import accounts as accounts_svc
from ..services import budgets as budgets_svc
from ..services import goals as goals_svc
from ..services import investments as investments_svc
from ..services import recurring as recurring_svc
from ..services import reports as reports_svc
from ..services import transactions as txn_svc
from ..services.settings import has_any_data
from ..utils import PERIODS, period_range, previous_period, today

bp = Blueprint("dashboard", __name__)

DASHBOARD_PERIODS = ["this_month", "last_month", "last_3_months", "this_year", "last_12_months"]


@bp.route("/")
def index():
    period = request.args.get("period")
    if period not in DASHBOARD_PERIODS:
        period = "this_month"
    start, end = period_range(period)
    prev_start, prev_end = previous_period(period)
    summary = reports_svc.dashboard_summary(period, start, end, prev_start, prev_end)
    now = today()
    monthly = reports_svc.monthly_series(12)
    holdings = investments_svc.list_holdings()
    budget = budgets_svc.month_overview(now.year, now.month)
    budget_top = sorted((line for line in budget["lines"] if line["budget_id"]),
                        key=lambda line: line["used_pct"] or 0, reverse=True)[:5]

    chart_data = {
        "monthly": [
            {"label": m["label"], "income": m["income_cents"], "expenses": m["expense_cents"], "net": m["net_cents"]}
            for m in monthly
        ],
        "categories": [
            {"label": c["name"], "value": c["total"]}
            for c in reports_svc.spending_by_category(start, end, top=7)["items"]
        ],
        "net_worth": [
            {"label": p["label"], "value": p["net_worth_cents"]} for p in reports_svc.net_worth_history(12)
        ],
    }
    return render_template(
        "dashboard.html",
        period=period,
        periods={k: PERIODS[k] for k in DASHBOARD_PERIODS},
        summary=summary,
        budget=budget,
        budget_top=budget_top,
        goals=goals_svc.list_goals()[:4],
        portfolio=investments_svc.portfolio_summary(holdings),
        accounts=accounts_svc.list_accounts(),
        recent=txn_svc.recent(8),
        due=recurring_svc.due_occurrences(),
        upcoming=recurring_svc.upcoming(14)[:5],
        chart_data=chart_data,
        has_data=has_any_data(),
        monthly=monthly,
    )
