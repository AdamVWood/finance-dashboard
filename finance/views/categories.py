from flask import Blueprint, abort, flash, redirect, render_template, request, url_for

from ..services import categories as categories_svc
from ..utils import ValidationError
from . import flash_validation

bp = Blueprint("categories", __name__, url_prefix="/categories")


@bp.route("/")
def index():
    show_archived = bool(request.args.get("archived"))
    cats = categories_svc.list_categories(include_archived=show_archived)
    return render_template(
        "categories/index.html",
        income=[c for c in cats if c["kind"] == "income"],
        expense=[c for c in cats if c["kind"] == "expense"],
        show_archived=show_archived,
    )


@bp.route("/new", methods=["GET", "POST"])
def create():
    if request.method == "POST":
        try:
            categories_svc.create_category(request.form)
        except ValidationError as exc:
            return render_template("categories/form.html", form=request.form, errors=exc.errors, category=None,
                                   kinds=categories_svc.KINDS), 422
        flash("Category added.", "success")
        return redirect(url_for(".index"))
    form = {"kind": request.args.get("kind", "expense"), "color": "#2a78d6"}
    return render_template("categories/form.html", form=form, errors={}, category=None, kinds=categories_svc.KINDS)


@bp.route("/<int:category_id>/edit", methods=["GET", "POST"])
def edit(category_id):
    category = categories_svc.get_category(category_id) or abort(404)
    others = [c for c in categories_svc.list_categories(category["kind"]) if c["id"] != category_id]
    if request.method == "POST":
        try:
            categories_svc.update_category(category_id, request.form)
        except ValidationError as exc:
            return render_template("categories/form.html", form=request.form, errors=exc.errors,
                                   category=category, kinds=categories_svc.KINDS, others=others), 422
        flash("Category updated.", "success")
        return redirect(url_for(".index"))
    form = {**category, "is_archived": "1" if category["is_archived"] else ""}
    usage = categories_svc.list_categories(include_archived=True)
    category["txn_count"] = next((c["txn_count"] for c in usage if c["id"] == category_id), 0)
    return render_template("categories/form.html", form=form, errors={}, category=category,
                           kinds=categories_svc.KINDS, others=others)


@bp.route("/<int:category_id>/delete", methods=["POST"])
def delete(category_id):
    try:
        categories_svc.delete_category(category_id, request.form.get("reassign_to") or None)
        flash("Category deleted.", "success")
        return redirect(url_for(".index"))
    except ValidationError as exc:
        flash_validation(exc)
        return redirect(url_for(".edit", category_id=category_id))
