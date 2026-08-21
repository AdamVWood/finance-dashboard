import sqlite3
import datetime
from app.categories import category_exists

DB_PATH = "database/finance.db"

# --- Helpers ---
def _connect():
    return sqlite3.connect(DB_PATH)

def get_date_range(option):
    today = datetime.date.today()
    if option == "this_month":
        start = today.replace(day=1)
        end = today
    elif option == "last_month":
        first_this_month = today.replace(day=1)
        last_month_end = first_this_month - datetime.timedelta(days=1)
        start = last_month_end.replace(day=1)
        end = last_month_end
    elif option == "last_3_months":
        start_month = today.month - 2
        start_year = today.year
        if start_month <= 0:
            start_month += 12
            start_year -= 1
        start = datetime.date(start_year, start_month, 1)
        end = today
    elif option == "this_year":
        start = datetime.date(today.year, 1, 1)
        end = today
    elif option == "all_time":
        start = datetime.date(1970, 1, 1)
        end = today
    else:
        return None, None
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")

# --- CRUD ---
def add_transaction(amount, transaction_type, category_id, description, date):
    if amount <= 0:
        raise ValueError("Amount must be greater than 0.")
    if not category_exists(category_id):
        raise ValueError("Category does not exist.")
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        raise ValueError("Invalid date format. Use YYYY-MM-DD.")

    created_at = datetime.datetime.today().strftime("%Y-%m-%d")

    conn = _connect()
    c = conn.cursor()
    c.execute(
        """INSERT INTO transactions (amount, transaction_type, category_id, description, date, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (amount, transaction_type, category_id, description, date, created_at)
    )
    conn.commit()
    conn.close()

def filter_transactions(mode="all", value=None):
    conn = _connect()
    c = conn.cursor()

    query = """
            SELECT t.id, t.date, t.description, c.name, t.transaction_type, t.amount, t.created_at
            FROM transactions t
                     INNER JOIN categories c ON t.category_id = c.id \
            """
    params = []
    order_clause = ""

    if mode == "keyword":
        keyword = f"%{value}%"
        query += " WHERE t.description LIKE ? OR c.name LIKE ? OR t.transaction_type LIKE ?"
        params = [keyword, keyword, keyword]

    elif mode == "category":
        query += " WHERE c.name = ?"
        params = [value]

    elif mode == "type":
        query += " WHERE t.transaction_type = ?"
        params = [value]

    elif mode == "date":
        start, end = value
        query += " WHERE t.date BETWEEN ? AND ?"
        params = [start, end]

    elif mode == "range":
        start, end = get_date_range(value)
        query += " WHERE t.date BETWEEN ? AND ?"
        params = [start, end]

    elif mode == "sort_date":
        order_clause = " ORDER BY t.date DESC"

    elif mode == "sort_amount":
        order_clause = " ORDER BY t.amount DESC"

    elif mode == "all":
        order_clause = " ORDER BY t.date DESC"

    c.execute(query + order_clause, params)
    rows = c.fetchall()
    conn.close()
    return rows

def view_transactions():
    """Return all transactions sorted by date (default view)."""
    return filter_transactions("all")

def search_transaction(transaction_id):
    """Return a single transaction by ID."""
    conn = _connect()
    c = conn.cursor()
    c.execute(
        """SELECT t.id, t.date, t.description, c.name, t.transaction_type, t.amount, t.created_at
           FROM transactions t
                    INNER JOIN categories c ON t.category_id = c.id
           WHERE t.id = ?""",
        (transaction_id,)
    )
    row = c.fetchone()
    conn.close()
    return row

def update_transaction(transaction_id, field, new_value):
    valid_fields = ["amount", "transaction_type", "category_id", "description", "date"]
    if field not in valid_fields:
        raise ValueError(f"Invalid field. Must be one of: {', '.join(valid_fields)}")

    conn = _connect()
    c = conn.cursor()
    c.execute(f"UPDATE transactions SET {field} = ? WHERE id = ?", (new_value, transaction_id))
    conn.commit()
    conn.close()

def delete_transaction(transaction_id):
    conn = _connect()
    c = conn.cursor()
    c.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
