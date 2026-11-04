from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..services import accounts as accounts_svc
from ..services import categories as categories_svc
from ..services import recurring as rec_svc
from ..services import transactions as txn_svc
from ..utils import ValidationError, today
from . import back, flash_validation

bp = Blueprint("recurring", __name__, url_prefix="/recurring")


def _ctx(**extra):
    return {
        "accounts": accounts_svc.list_accounts(),
        "income_categories": categories_svc.list_categories("income"),
        "expense_categories": categories_svc.list_categories("expense"),
        "types": txn_svc.TYPES,
        "frequencies": rec_svc.FREQUENCIES,
        **extra,
    }


@bp.route("/")
def index():
    items = rec_svc.list_items()
    due = rec_svc.due_occurrences()
    monthly_factor = {"weekly": 52 / 12, "biweekly": 26 / 12, "monthly": 1, "quarterly": 1 / 3, "yearly": 1 / 12}
    active = [i for i in items if i["is_active"] and not i["finished"]]
    monthly_in = sum(i["amount_cents"] * monthly_factor[i["frequency"]] for i in active if i["type"] == "income")
    monthly_out = sum(i["amount_cents"] * monthly_factor[i["frequency"]] for i in active if i["type"] == "expense")
    return render_template("recurring/index.html", items=items, due=due, monthly_in=monthly_in,
                           monthly_out=monthly_out, upcoming=rec_svc.upcoming(30))


@bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        try:
            rec_svc.create_item(request.form)
        except ValidationError as exc:
            return render_template("recurring/form.html", **_ctx(form=request.form, errors=exc.errors, item=None)), 422
        flash("Recurring item added.", "success")
        return redirect(url_for(".index"))
    form = {"type": "expense", "frequency": "monthly", "start_date": today().isoformat()}
    return render_template("recurring/form.html", **_ctx(form=form, errors={}, item=None))


@bp.route("/<int:item_id>/edit", methods=["GET", "POST"])
def edit(item_id):
    item = rec_svc.get_item(item_id) or abort(404)
    if request.method == "POST":
        try:
            rec_svc.update_item(item_id, request.form)
        except ValidationError as exc:
            return render_template("recurring/form.html", **_ctx(form=request.form, errors=exc.errors, item=item)), 422
        flash("Recurring item updated.", "success")
        return redirect(url_for(".index"))
    return render_template("recurring/form.html", **_ctx(form=rec_svc.to_form(item), errors={}, item=item))


@bp.route("/<int:item_id>/delete", methods=["POST"])
def delete(item_id):
    try:
        rec_svc.delete_item(item_id)
        flash("Recurring item deleted. Transactions it already created are kept.", "success")
    except ValidationError as exc:
        flash_validation(exc)
    return redirect(url_for(".index"))


@bp.route("/post", methods=["POST"])
def post_due():
    item_id = request.form.get("item_id", type=int)
    try:
        count = rec_svc.post_due(item_id)
    except ValidationError as exc:
        flash("A recurring item couldn't be posted: " + " ".join(exc.errors.values()), "error")
        return back(".index")
    flash(f"Posted {count} transaction(s)." if count else "Nothing was due.", "success" if count else "info")
    return back(".index")


@bp.route("/<int:item_id>/skip", methods=["POST"])
def skip(item_id):
    try:
        rec_svc.skip_next(item_id)
        flash("Skipped the next occurrence.", "success")
    except ValidationError as exc:
        flash_validation(exc)
    return back(".index")
