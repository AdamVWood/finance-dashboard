"""Income and expense categories."""

import re

from ..db import get_db
from ..utils import ValidationError, Validator

KINDS = {"income": "Income", "expense": "Expense"}
HEX_COLOR = re.compile(r"^#[0-9a-fA-F]{6}$")


def list_categories(kind=None, include_archived=False):
    sql = """
        SELECT c.*,
               (SELECT COUNT(*) FROM transactions t WHERE t.category_id = c.id) AS txn_count,
               (SELECT COUNT(*) FROM recurring r WHERE r.category_id = c.id) AS recurring_count
        FROM categories c WHERE 1=1"""
    params = []
    if kind:
        sql += " AND c.kind = ?"
        params.append(kind)
    if not include_archived:
        sql += " AND c.is_archived = 0"
    sql += " ORDER BY c.kind DESC, c.name COLLATE NOCASE"
    return [dict(r) for r in get_db().execute(sql, params)]


def get_category(category_id):
    row = get_db().execute("SELECT * FROM categories WHERE id = ?", (category_id,)).fetchone()
    return dict(row) if row else None


def find_by_name(name, kind):
    row = get_db().execute(
        "SELECT * FROM categories WHERE name = ? COLLATE NOCASE AND kind = ?", (name.strip(), kind)
    ).fetchone()
    return dict(row) if row else None


def _validate(form, category_id=None):
    v = Validator(form)
    name = v.text("name", "Name", max_length=60)
    kind = v.choice("kind", "Type", KINDS)
    color = v.raw("color") or None
    if color and not HEX_COLOR.match(color):
        v.error("color", "Colour must be a hex value like #2a78d6.")
    if name and kind:
        clash = get_db().execute(
            "SELECT id FROM categories WHERE name = ? COLLATE NOCASE AND kind = ? AND id IS NOT ?",
            (name, kind, category_id),
        ).fetchone()
        if clash:
            v.error("name", f"A {kind} category called '{name}' already exists.")
    if category_id and kind:
        current = get_category(category_id)
        if current and current["kind"] != kind:
            used = get_db().execute(
                """SELECT (SELECT COUNT(*) FROM transactions WHERE category_id = :id)
                        + (SELECT COUNT(*) FROM budgets WHERE category_id = :id)
                        + (SELECT COUNT(*) FROM recurring WHERE category_id = :id)""",
                {"id": category_id},
            ).fetchone()[0]
            if used:
                v.error("kind", "This category is already in use, so its type can't be changed.")
    v.raise_if_errors()
    return {"name": name, "kind": kind, "color": color, "is_archived": v.flag("is_archived")}


def create_category(form):
    data = _validate(form)
    db = get_db()
    cur = db.execute(
        "INSERT INTO categories (name, kind, color, is_archived) VALUES (:name, :kind, :color, :is_archived)",
        data,
    )
    db.commit()
    return cur.lastrowid


def get_or_create(name, kind):
    existing = find_by_name(name, kind)
    if existing:
        return existing["id"]
    db = get_db()
    return db.execute("INSERT INTO categories (name, kind) VALUES (?, ?)", (name.strip(), kind)).lastrowid


def update_category(category_id, form):
    if not get_category(category_id):
        raise ValidationError("Category not found.")
    data = _validate(form, category_id)
    data["id"] = category_id
    db = get_db()
    db.execute(
        "UPDATE categories SET name=:name, kind=:kind, color=:color, is_archived=:is_archived WHERE id=:id",
        data,
    )
    db.commit()


def delete_category(category_id, reassign_to=None):
    """Delete a category. If it has transactions, they must be moved first.

    ``reassign_to`` is the id of a category of the same kind that receives
    the transactions and recurring items. Budgets for the deleted category
    are removed.
    """
    db = get_db()
    category = get_category(category_id)
    if not category:
        raise ValidationError("Category not found.")
    in_use = db.execute(
        "SELECT (SELECT COUNT(*) FROM transactions WHERE category_id = :id)"
        " + (SELECT COUNT(*) FROM recurring WHERE category_id = :id)",
        {"id": category_id},
    ).fetchone()[0]
    if in_use:
        if not reassign_to:
            raise ValidationError(
                {"reassign_to": "This category is in use. Choose another category to move its transactions to."}
            )
        target = get_category(int(reassign_to))
        if not target or target["id"] == category_id or target["kind"] != category["kind"]:
            raise ValidationError({"reassign_to": "Choose a different category of the same type."})
        db.execute("UPDATE transactions SET category_id = ? WHERE category_id = ?", (target["id"], category_id))
        db.execute("UPDATE recurring SET category_id = ? WHERE category_id = ?", (target["id"], category_id))
    db.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    db.commit()
