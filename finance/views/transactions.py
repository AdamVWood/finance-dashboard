import datetime as dt

from flask import Blueprint, Response, abort, flash, redirect, render_template, request, url_for

from ..services import accounts as accounts_svc
from ..services import categories as categories_svc
from ..services import transactions as txn_svc
from ..utils import ValidationError, today
from . import back, flash_validation

bp = Blueprint("transactions", __name__, url_prefix="/transactions")


def _form_context(txn=None, **extra):
    # When editing, keep an archived account/category selectable if this transaction uses it.
    keep_accounts = {txn["account_id"], txn["to_account_id"]} if txn else set()
    keep_cat = txn["category_id"] if txn else None
    accounts = [a for a in accounts_svc.list_accounts(include_archived=True)
                if not a["is_archived"] or a["id"] in keep_accounts]
    cats = [c for c in categories_svc.list_categories(include_archived=True)
            if not c["is_archived"] or c["id"] == keep_cat]
    return {
        "txn": txn,
        "accounts": accounts,
        "income_categories": [c for c in cats if c["kind"] == "income"],
        "expense_categories": [c for c in cats if c["kind"] == "expense"],
        "types": txn_svc.TYPES,
        **extra,
    }


@bp.route("/")
def index():
    filters, errors = txn_svc.parse_filters(request.args)
    for e in errors:
        flash(e, "error")
    page = request.args.get("page", 1, type=int)
    result = txn_svc.search(filters, page=page)
    active = any(filters[k] for k in ("q", "type", "category_id", "account_id", "start", "end", "min", "max"))
    return render_template(
        "transactions/index.html",
        result=result,
        filters=filters,
        filters_active=active,
        categories=categories_svc.list_categories(include_archived=True),
        accounts=accounts_svc.list_accounts(include_archived=True),
        types=txn_svc.TYPES,
        sorts={"date_desc": "Newest first", "date_asc": "Oldest first", "amount_desc": "Largest amount",
               "amount_asc": "Smallest amount", "description": "Description A–Z"},
    )


@bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        try:
            txn_svc.create_transaction(request.form)
        except ValidationError as exc:
            return render_template("transactions/form.html", **_form_context(
                form=request.form, errors=exc.errors, txn=None)), 422
        flash("Transaction added.", "success")
        if request.form.get("add_another"):
            return redirect(url_for(".create", type=request.form.get("type"),
                                    account_id=request.form.get("account_id"), date=request.form.get("date")))
        return back(".index")
    form = {
        "type": request.args.get("type", "expense"),
        "date": request.args.get("date") or today().isoformat(),
        "account_id": request.args.get("account_id", ""),
    }
    return render_template("transactions/form.html", **_form_context(form=form, errors={}, txn=None))


@bp.route("/<int:txn_id>/edit", methods=["GET", "POST"])
def edit(txn_id):
    txn = txn_svc.get_transaction(txn_id) or abort(404)
    if request.method == "POST":
        try:
            txn_svc.update_transaction(txn_id, request.form)
        except ValidationError as exc:
            return render_template("transactions/form.html", **_form_context(
                form=request.form, errors=exc.errors, txn=txn)), 422
        flash("Transaction updated.", "success")
        return back(".index")
    return render_template("transactions/form.html", **_form_context(form=txn_svc.to_form(txn), errors={}, txn=txn))


@bp.route("/<int:txn_id>/duplicate")
def duplicate(txn_id):
    txn = txn_svc.get_transaction(txn_id) or abort(404)
    form = {**txn_svc.to_form(txn), "date": today().isoformat()}
    return render_template("transactions/form.html", **_form_context(form=form, errors={}, txn=None))


@bp.route("/<int:txn_id>/delete", methods=["POST"])
def delete(txn_id):
    try:
        txn_svc.delete_transaction(txn_id)
        flash("Transaction deleted.", "success")
    except ValidationError as exc:
        flash_validation(exc)
    return back(".index")


@bp.route("/bulk-delete", methods=["POST"])
def bulk_delete():
    count = txn_svc.delete_many(request.form.getlist("ids"))
    flash(f"{count} transaction(s) deleted." if count else "No transactions were selected.",
          "success" if count else "info")
    return back(".index")


@bp.route("/export.csv")
def export():
    filters, _ = txn_svc.parse_filters(request.args)
    body = txn_svc.export_csv(filters)
    name = f"transactions-{dt.date.today():%Y%m%d}.csv"
    return Response(body, mimetype="text/csv", headers={"Content-Disposition": f"attachment; filename={name}"})


@bp.route("/import", methods=["GET", "POST"])
def import_csv():
    context = {"accounts": accounts_svc.list_accounts(), "columns": txn_svc.CSV_COLUMNS, "problems": []}
    if request.method == "POST":
        upload = request.files.get("file")
        if not upload or not upload.filename:
            flash("Choose a CSV file to import.", "error")
            return render_template("transactions/import.html", **context), 422
        try:
            text = upload.read().decode("utf-8-sig")
        except UnicodeDecodeError:
            flash("The file must be a UTF-8 encoded CSV.", "error")
            return render_template("transactions/import.html", **context), 422
        default_account = request.form.get("default_account_id", type=int)
        try:
            count = txn_svc.import_csv(text, default_account, create_categories=bool(request.form.get("create")))
        except ValidationError as exc:
            flash_validation(exc)
            context["problems"] = exc.errors.get("rows", [])
            return render_template("transactions/import.html", **context), 422
        flash(f"Imported {count} transaction(s).", "success")
        return redirect(url_for(".index"))
    return render_template("transactions/import.html", **context)


@bp.route("/template.csv")
def csv_template():
    sample = (
        ",".join(txn_svc.CSV_COLUMNS) + "\n"
        f"{today().isoformat()},Supermarket,expense,85.40,Groceries,Everyday chequing,,\n"
        f"{today().isoformat()},Monthly salary,income,4200.00,Salary,Everyday chequing,,\n"
        f"{today().isoformat()},Move to savings,transfer,500.00,,Everyday chequing,High-interest savings,\n"
    )
    return Response(sample, mimetype="text/csv",
                    headers={"Content-Disposition": "attachment; filename=transactions-template.csv"})
