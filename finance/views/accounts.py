from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..services import accounts as accounts_svc
from ..services import reports as reports_svc
from ..services import transactions as txn_svc
from ..utils import ValidationError, cents_to_input, today
from . import flash_validation

bp = Blueprint("accounts", __name__, url_prefix="/accounts")


@bp.route("/")
def index():
    accounts = accounts_svc.list_accounts(include_archived=True)
    worth = reports_svc.net_worth()
    history = reports_svc.net_worth_history(12)
    chart = {
        "series": [
            {"label": p["label"], "assets": p["assets_cents"], "liabilities": p["liabilities_cents"],
             "net": p["net_worth_cents"]}
            for p in history
        ]
    }
    return render_template("accounts/index.html", accounts=accounts, worth=worth, history=history, chart=chart)


@bp.route("/<int:account_id>")
def detail(account_id):
    account = accounts_svc.get_account(account_id) or abort(404)
    filters, _ = txn_svc.parse_filters({"account_id": str(account_id)})
    result = txn_svc.search(filters, page=request.args.get("page", 1, type=int), page_size=25)
    return render_template("accounts/detail.html", account=account, result=result)


def _to_form(acc):
    opening = acc["opening_balance_cents"]
    return {
        "name": acc["name"],
        "type": acc["type"],
        "institution": acc["institution"] or "",
        "opening_balance": cents_to_input(-opening if acc["is_liability"] else opening),
        "opened_on": acc["opened_on"],
        "notes": acc["notes"] or "",
        "is_archived": "1" if acc["is_archived"] else "",
    }


@bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        try:
            accounts_svc.create_account(request.form)
        except ValidationError as exc:
            return render_template("accounts/form.html", form=request.form, errors=exc.errors, account=None,
                                   types=accounts_svc.ACCOUNT_TYPES, liability_types=accounts_svc.LIABILITY_TYPES), 422
        flash("Account added.", "success")
        return redirect(url_for(".index"))
    form = {"type": request.args.get("type", "checking"), "opened_on": today().isoformat()}
    return render_template("accounts/form.html", form=form, errors={}, account=None,
                           types=accounts_svc.ACCOUNT_TYPES, liability_types=accounts_svc.LIABILITY_TYPES)


@bp.route("/<int:account_id>/edit", methods=["GET", "POST"])
def edit(account_id):
    account = accounts_svc.get_account(account_id) or abort(404)
    if request.method == "POST":
        try:
            accounts_svc.update_account(account_id, request.form)
        except ValidationError as exc:
            return render_template("accounts/form.html", form=request.form, errors=exc.errors, account=account,
                                   types=accounts_svc.ACCOUNT_TYPES, liability_types=accounts_svc.LIABILITY_TYPES), 422
        flash("Account updated.", "success")
        return redirect(url_for(".detail", account_id=account_id))
    return render_template("accounts/form.html", form=_to_form(account), errors={}, account=account,
                           types=accounts_svc.ACCOUNT_TYPES, liability_types=accounts_svc.LIABILITY_TYPES)


@bp.route("/<int:account_id>/delete", methods=["POST"])
def delete(account_id):
    try:
        accounts_svc.delete_account(account_id)
        flash("Account deleted.", "success")
        return redirect(url_for(".index"))
    except ValidationError as exc:
        flash_validation(exc)
        return redirect(url_for(".detail", account_id=account_id))
