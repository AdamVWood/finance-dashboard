import datetime
from app.categories import category_exists
from database.database import get_connection

VALID_TYPES = ["Withdrawal", "Deposit", "Transfer", "Remittance", "Direct Debit", "Fee"]


def get_date_range(option):
    """Returns (start_date_str, end_date_str) for a named range option, or (None, None) if invalid."""
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


def add_transaction(data):
    errors = []

    amount = None
    try:
        amount = float(data.get("amount"))
        if amount <= 0:
            errors.append("Amount must be greater than 0.")
    except (TypeError, ValueError):
        errors.append("Amount must be a valid number.")

    transaction_type = (data.get("transaction_type") or "").strip()
    if transaction_type not in VALID_TYPES:
        errors.append(f"Invalid transaction type. Must be one of: {', '.join(VALID_TYPES)}")

    category_id = None
    try:
        category_id = int(data.get("category_id"))
        if category_id <= 0:
            errors.append("Category ID must be a positive integer.")
        elif not category_exists(category_id):
            errors.append("Category does not exist.")
    except (TypeError, ValueError):
        errors.append("Category ID must be a valid integer.")

    description = (data.get("description") or "").strip()

    date = (data.get("date") or "").strip()
    try:
        datetime.datetime.strptime(date, "%Y-%m-%d")
    except ValueError:
        errors.append("Invalid date format. Use YYYY-MM-DD.")

    if errors:
        return False, errors

    created_at = datetime.datetime.today().strftime("%Y-%m-%d")

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO transactions (amount, transaction_type, category_id, description, date, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (amount, transaction_type, category_id, description, date, created_at),
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return True, {"id": new_id}


def get_all_transactions():
    """Returns all transactions (default view), sorted by date desc."""
    success, rows = filter_transactions("all")
    return rows


def get_transaction(transaction_id):
    """Returns a single transaction dict, or None if it doesn't exist."""
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """SELECT t.id, t.date, t.description, c.name AS category_name, t.category_id,
                  t.transaction_type, t.amount, t.created_at
           FROM transactions t
                    INNER JOIN categories c ON t.category_id = c.id
           WHERE t.id = ?""",
        (transaction_id,),
    )
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def filter_transactions(mode="all", **kwargs):
    conn = get_connection()
    c = conn.cursor()

    query = """
            SELECT t.id, t.date, t.description, c.name AS category_name, t.category_id,
                   t.transaction_type, t.amount, t.created_at
            FROM transactions t
                     INNER JOIN categories c ON t.category_id = c.id \
            """
    params = []
    order_clause = ""

    if mode == "keyword":
        keyword = (kwargs.get("keyword") or "").strip()
        if not keyword:
            conn.close()
            return False, "Keyword cannot be empty."
        query += " WHERE t.description LIKE ? OR c.name LIKE ? OR t.transaction_type LIKE ?"
        params = [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]

    elif mode == "category":
        category = (kwargs.get("category") or "").strip()
        if not category:
            conn.close()
            return False, "Category cannot be empty."
        query += " WHERE c.name = ?"
        params = [category]

    elif mode == "type":
        transaction_type = (kwargs.get("transaction_type") or "").strip()
        if transaction_type not in VALID_TYPES:
            conn.close()
            return False, f"Invalid type. Must be one of: {', '.join(VALID_TYPES)}"
        query += " WHERE t.transaction_type = ?"
        params = [transaction_type]

    elif mode == "date":
        start_date = (kwargs.get("start_date") or "").strip()
        end_date = (kwargs.get("end_date") or "").strip()
        try:
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                conn.close()
                return False, "Start date cannot be after end date."
        except ValueError:
            conn.close()
            return False, "Dates must be in YYYY-MM-DD format."
        query += " WHERE t.date BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "range":
        range_option = kwargs.get("range_option")
        start_date, end_date = get_date_range(range_option)
        if start_date is None:
            conn.close()
            return False, "Invalid range option."
        query += " WHERE t.date BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "sort_date":
        order_clause = " ORDER BY t.date DESC"

    elif mode == "sort_amount":
        order_clause = " ORDER BY t.amount DESC"

    elif mode == "all":
        order_clause = " ORDER BY t.date DESC"

    else:
        conn.close()
        return False, f"Unknown filter mode: {mode}"

    c.execute(query + order_clause, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return True, rows


def update_transaction_field(transaction_id, field, value):
    valid_fields = ["amount", "transaction_type", "category_id", "description", "date"]
    if field not in valid_fields:
        return False, f"Invalid field. Must be one of: {', '.join(valid_fields)}"

    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
    if c.fetchone() is None:
        conn.close()
        return False, "Transaction does not exist."

    if field == "amount":
        try:
            value = float(value)
            if value <= 0:
                conn.close()
                return False, "Amount must be greater than 0."
        except (TypeError, ValueError):
            conn.close()
            return False, "Amount must be a valid number."

    elif field == "transaction_type":
        if value not in VALID_TYPES:
            conn.close()
            return False, f"Invalid type. Must be one of: {', '.join(VALID_TYPES)}"

    elif field == "category_id":
        try:
            value = int(value)
            if value <= 0 or not category_exists(value):
                conn.close()
                return False, "Category does not exist."
        except (TypeError, ValueError):
            conn.close()
            return False, "Category ID must be a valid integer."

    elif field == "date":
        try:
            datetime.datetime.strptime(value, "%Y-%m-%d")
        except (TypeError, ValueError):
            conn.close()
            return False, "Invalid date format. Use YYYY-MM-DD."

    c.execute(f"UPDATE transactions SET {field} = ? WHERE id = ?", (value, transaction_id))
    conn.commit()
    conn.close()
    return True, None


def delete_transaction(transaction_id):
    """Returns (success: bool, error: str|None)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
    if c.fetchone() is None:
        conn.close()
        return False, "Transaction does not exist."
    c.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
    conn.commit()
    conn.close()
    return True, None