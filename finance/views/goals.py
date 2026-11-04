from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..services import goals as goals_svc
from ..utils import ValidationError, parse_date, today
from . import flash_validation

bp = Blueprint("goals", __name__, url_prefix="/goals")


@bp.route("/")
def index():
    show_archived = bool(request.args.get("archived"))
    goals = goals_svc.list_goals(include_archived=show_archived)
    active = [g for g in goals if not g["is_archived"]]
    return render_template(
        "goals/index.html",
        goals=goals,
        show_archived=show_archived,
        saved=sum(g["saved_cents"] for g in active),
        target=sum(g["target_cents"] for g in active),
        monthly_needed=sum(g["required_monthly_cents"] or 0 for g in active),
    )


@bp.route("/<int:goal_id>")
def detail(goal_id):
    goal = goals_svc.get_goal(goal_id) or abort(404)
    series = goals_svc.progress_series(goal_id)
    chart = {"points": [{"label": parse_date(p["date"]).strftime("%d %b %y").lstrip("0"), "value": p["saved_cents"]} for p in series],
             "target": goal["target_cents"]}
    return render_template("goals/detail.html", goal=goal, contributions=goals_svc.contributions(goal_id),
                           chart=chart, errors={}, form={"date": today().isoformat()})


@bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        try:
            goal_id = goals_svc.create_goal(request.form)
        except ValidationError as exc:
            return render_template("goals/form.html", form=request.form, errors=exc.errors, goal=None), 422
        flash("Savings goal created.", "success")
        return redirect(url_for(".detail", goal_id=goal_id))
    return render_template("goals/form.html", form={"start_date": today().isoformat()}, errors={}, goal=None)


@bp.route("/<int:goal_id>/edit", methods=["GET", "POST"])
def edit(goal_id):
    goal = goals_svc.get_goal(goal_id) or abort(404)
    if request.method == "POST":
        try:
            goals_svc.update_goal(goal_id, request.form)
        except ValidationError as exc:
            return render_template("goals/form.html", form=request.form, errors=exc.errors, goal=goal), 422
        flash("Goal updated.", "success")
        return redirect(url_for(".detail", goal_id=goal_id))
    return render_template("goals/form.html", form=goals_svc.to_form(goal), errors={}, goal=goal)


@bp.route("/<int:goal_id>/delete", methods=["POST"])
def delete(goal_id):
    try:
        goals_svc.delete_goal(goal_id)
        flash("Goal deleted.", "success")
    except ValidationError as exc:
        flash_validation(exc)
    return redirect(url_for(".index"))


@bp.route("/<int:goal_id>/contribute", methods=["POST"])
def contribute(goal_id):
    goal = goals_svc.get_goal(goal_id) or abort(404)
    try:
        goals_svc.add_contribution(goal_id, request.form)
    except ValidationError as exc:
        series = goals_svc.progress_series(goal_id)
        chart = {"points": [{"label": parse_date(p["date"]).strftime("%d %b %y").lstrip("0"), "value": p["saved_cents"]} for p in series],
                 "target": goal["target_cents"]}
        return render_template("goals/detail.html", goal=goal, contributions=goals_svc.contributions(goal_id),
                               chart=chart, errors=exc.errors, form=request.form), 422
    withdrawing = request.form.get("direction") == "withdraw"
    flash("Withdrawal recorded." if withdrawing else "Contribution added.", "success")
    if request.form.get("next") == "index":
        return redirect(url_for(".index"))
    return redirect(url_for(".detail", goal_id=goal_id))


@bp.route("/contributions/<int:contribution_id>/delete", methods=["POST"])
def delete_contribution(contribution_id):
    try:
        goal_id = goals_svc.delete_contribution(contribution_id)
        flash("Entry removed.", "success")
        return redirect(url_for(".detail", goal_id=goal_id))
    except ValidationError as exc:
        flash_validation(exc)
        return redirect(url_for(".index"))
