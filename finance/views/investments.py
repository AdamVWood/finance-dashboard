from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..services import accounts as accounts_svc
from ..services import investments as inv_svc
from ..utils import ValidationError, parse_date, today
from . import flash_validation

bp = Blueprint("investments", __name__, url_prefix="/investments")

SORTS = {"value": "Value", "return": "Return", "name": "Name", "type": "Asset type", "date": "Purchase date"}


@bp.route("/")
def index():
    sort = request.args.get("sort") if request.args.get("sort") in SORTS else "value"
    holdings = inv_svc.list_holdings(sort)
    summary = inv_svc.portfolio_summary(holdings)
    chart = {"allocation": [{"label": a["label"], "value": a["value_cents"]} for a in summary["allocation"]]}
    sold = inv_svc.list_holdings("date", sold=True)
    return render_template("investments/index.html", holdings=holdings, summary=summary, chart=chart,
                           sort=sort, sorts=SORTS, sold=sold, realised=inv_svc.realised_summary(sold))


@bp.route("/<int:holding_id>")
def detail(holding_id):
    holding = inv_svc.get_holding(holding_id) or abort(404)
    history = inv_svc.price_history(holding_id)
    chart = {"points": [{"label": parse_date(p["date"]).strftime("%d %b %y").lstrip("0"),
                         "value": round(p["price"] * holding["quantity"] * 100)}
                        for p in history]}
    return render_template("investments/detail.html", h=holding, history=history, chart=chart,
                           accounts=accounts_svc.list_accounts(), errors={},
                           form={"sold_on": today().isoformat(), "sale_price": inv_svc.to_form(holding)["current_price"]})


@bp.route("/<int:holding_id>/sell", methods=["POST"])
def sell(holding_id):
    holding = inv_svc.get_holding(holding_id) or abort(404)
    try:
        inv_svc.sell_holding(holding_id, request.form)
    except ValidationError as exc:
        history = inv_svc.price_history(holding_id)
        chart = {"points": [{"label": parse_date(p["date"]).strftime("%d %b %y").lstrip("0"),
                         "value": round(p["price"] * holding["quantity"] * 100)}
                            for p in history]}
        return render_template("investments/detail.html", h=holding, history=history, chart=chart,
                               accounts=accounts_svc.list_accounts(), errors=exc.errors, form=request.form), 422
    flash("Sale recorded.", "success")
    return redirect(url_for(".detail", holding_id=holding_id))


@bp.route("/<int:holding_id>/undo-sale", methods=["POST"])
def undo_sale(holding_id):
    try:
        inv_svc.undo_sale(holding_id)
        flash("Sale undone - the holding is open again.", "success")
    except ValidationError as exc:
        flash_validation(exc)
    return redirect(url_for(".detail", holding_id=holding_id))


@bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        try:
            inv_svc.create_holding(request.form)
        except ValidationError as exc:
            return render_template("investments/form.html", form=request.form, errors=exc.errors, h=None,
                                   types=inv_svc.ASSET_TYPES, accounts=accounts_svc.list_accounts()), 422
        flash("Investment added.", "success")
        return redirect(url_for(".index"))
    form = {"purchase_date": today().isoformat(), "asset_type": "etf"}
    return render_template("investments/form.html", form=form, errors={}, h=None, types=inv_svc.ASSET_TYPES,
                           accounts=accounts_svc.list_accounts())


@bp.route("/<int:holding_id>/edit", methods=["GET", "POST"])
def edit(holding_id):
    holding = inv_svc.get_holding(holding_id) or abort(404)
    if request.method == "POST":
        try:
            inv_svc.update_holding(holding_id, request.form)
        except ValidationError as exc:
            return render_template("investments/form.html", form=request.form, errors=exc.errors, h=holding,
                                   types=inv_svc.ASSET_TYPES, accounts=accounts_svc.list_accounts()), 422
        flash("Investment updated.", "success")
        return redirect(url_for(".detail", holding_id=holding_id))
    return render_template("investments/form.html", form=inv_svc.to_form(holding), errors={}, h=holding,
                           types=inv_svc.ASSET_TYPES, accounts=accounts_svc.list_accounts())


@bp.route("/<int:holding_id>/delete", methods=["POST"])
def delete(holding_id):
    try:
        inv_svc.delete_holding(holding_id)
        flash("Investment deleted.", "success")
    except ValidationError as exc:
        flash_validation(exc)
    return redirect(url_for(".index"))


@bp.route("/prices", methods=["GET", "POST"])
def prices():
    holdings = inv_svc.list_holdings("name")
    if request.method == "POST":
        submitted = {
            int(k.split("_", 1)[1]): v for k, v in request.form.items()
            if k.startswith("price_") and k.split("_", 1)[1].isdigit()
        }
        v_date = request.form.get("date") or today().isoformat()
        try:
            if v_date > today().isoformat():
                raise ValidationError({"date": "The price date can't be in the future."})
            count = inv_svc.update_prices(submitted, v_date)
        except ValidationError as exc:
            flash_validation(exc) if "date" in exc.errors else flash("Check the highlighted prices.", "error")
            return render_template("investments/prices.html", holdings=holdings, errors=exc.errors,
                                   submitted=request.form, date=v_date), 422
        flash(f"Updated {count} price(s)." if count else "No prices were changed.", "success" if count else "info")
        return redirect(url_for(".index"))
    return render_template("investments/prices.html", holdings=holdings, errors={}, submitted={},
                           date=today().isoformat())
