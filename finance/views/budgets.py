import datetime as dt

from flask import Blueprint, flash, redirect, render_template, request, url_for

from ..services import budgets as budgets_svc
from ..utils import ValidationError, add_months, month_label, today
from . import flash_validation

bp = Blueprint("budgets", __name__, url_prefix="/budgets")


def _period():
    now = today()
    year = request.values.get("year", now.year, type=int)
    month = request.values.get("month", now.month, type=int)
    if not (1990 <= year <= 2100 and 1 <= month <= 12):
        year, month = now.year, now.month
    return year, month


@bp.route("/")
def index():
    year, month = _period()
    current = dt.date(year, month, 1)
    prev, nxt = add_months(current, -1), add_months(current, 1)
    overview = budgets_svc.month_overview(year, month)
    return render_template(
        "budgets/index.html",
        o=overview,
        label=month_label(year, month, short=False),
        prev=prev,
        nxt=nxt,
        is_current=(year, month) == (today().year, today().month),
        suggestions=budgets_svc.suggested_amounts(year, month),
        editing=bool(request.args.get("edit")) or not overview["has_budgets"],
        errors={},
    )


@bp.route("/save", methods=["POST"])
def save():
    year, month = _period()
    amounts = {
        int(key.split("_", 1)[1]): value
        for key, value in request.form.items()
        if key.startswith("amount_") and key.split("_", 1)[1].isdigit()
    }
    try:
        budgets_svc.save_month(year, month, amounts)
        flash(f"Budgets for {month_label(year, month, short=False)} saved.", "success")
    except ValidationError as exc:
        flash("Some budgets weren't saved - check the highlighted amounts.", "error")
        current = dt.date(year, month, 1)
        return render_template(
            "budgets/index.html",
            o=budgets_svc.month_overview(year, month),
            label=month_label(year, month, short=False),
            prev=add_months(current, -1), nxt=add_months(current, 1),
            is_current=(year, month) == (today().year, today().month),
            suggestions=budgets_svc.suggested_amounts(year, month),
            editing=True, errors=exc.errors, submitted=request.form,
        ), 422
    return redirect(url_for(".index", year=year, month=month))


@bp.route("/copy", methods=["POST"])
def copy_previous():
    year, month = _period()
    count = budgets_svc.copy_from_previous(year, month, overwrite=bool(request.form.get("overwrite")))
    flash(f"Copied {count} budget(s) from the previous month." if count
          else "Nothing to copy - the previous month has no budgets (or they already exist here).",
          "success" if count else "info")
    return redirect(url_for(".index", year=year, month=month))


@bp.route("/clear", methods=["POST"])
def clear():
    year, month = _period()
    count = budgets_svc.clear_month(year, month)
    flash(f"Removed {count} budget(s).", "success")
    return redirect(url_for(".index", year=year, month=month))


@bp.route("/set", methods=["POST"])
def set_one():
    try:
        budgets_svc.set_budget(request.form)
        flash("Budget saved.", "success")
    except ValidationError as exc:
        flash_validation(exc)
    year, month = _period()
    return redirect(url_for(".index", year=year, month=month))
