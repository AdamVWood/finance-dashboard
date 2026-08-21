from database.database import get_connection


def category_exists(category_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
    result = c.fetchone()
    conn.close()
    return result is not None


def get_all_categories():
    """Returns a list of dicts, one per category, sorted by name."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name FROM categories ORDER BY name ASC")
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_category(category_id):
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id, name FROM categories WHERE id = ?", (category_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def search_categories(keyword):
    keyword = (keyword or "").strip()
    if not keyword:
        return False, "Keyword cannot be empty."

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT id, name FROM categories WHERE LOWER(name) LIKE LOWER(?)",
        (f"%{keyword}%",),
    )
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return True, rows


def add_category(name):
    name = (name or "").strip()
    if not name:
        return False, "Category name cannot be empty."

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM categories WHERE LOWER(name) = LOWER(?)", (name,))
    if c.fetchone():
        conn.close()
        return False, "Category with this name already exists."

    c.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return True, {"id": new_id}


def update_category(category_id, name):
    """Returns (success: bool, error: str|None)."""
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
    if c.fetchone() is None:
        conn.close()
        return False, "Category does not exist."

    name = (name or "").strip()
    if not name:
        conn.close()
        return False, "Category name cannot be empty."

    c.execute(
        "SELECT id FROM categories WHERE LOWER(name) = LOWER(?) AND id != ?",
        (name, category_id),
    )
    if c.fetchone():
        conn.close()
        return False, "Category with this name already exists."

    c.execute("UPDATE categories SET name = ? WHERE id = ?", (name, category_id))
    conn.commit()
    conn.close()
    return True, None


def get_linked_transaction_count(category_id):
    """Returns the number of transactions linked to this category (for delete warnings)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM transactions WHERE category_id = ?", (category_id,))
    count = c.fetchone()[0]
    conn.close()
    return count


def delete_category(category_id):
    """Returns (success: bool, error: str|None)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
    if c.fetchone() is None:
        conn.close()
        return False, "Category does not exist."
    c.execute("DELETE FROM categories WHERE id = ?", (category_id,))
    conn.commit()
    conn.close()
    return True, None