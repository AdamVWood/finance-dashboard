import datetime
from app.categories import category_exists
from database.database import get_connection

VALID_TYPES = ["Stock", "ETF", "Bond", "Crypto", "Other"]


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


def add_investment(data):
    errors = []

    name = (data.get("name") or "").strip()
    if not name:
        errors.append("Name cannot be empty.")

    ticker = (data.get("ticker") or "").strip().upper()
    if not ticker:
        errors.append("Ticker cannot be empty.")

    asset_type = (data.get("asset_type") or "").strip().title()
    if asset_type not in VALID_TYPES:
        errors.append(f"Invalid asset type. Must be one of: {', '.join(VALID_TYPES)}")

    category_id = None
    try:
        category_id = int(data.get("category_id"))
        if category_id <= 0:
            errors.append("Category ID must be a positive integer.")
        elif not category_exists(category_id):
            errors.append("Category does not exist.")
    except (TypeError, ValueError):
        errors.append("Category ID must be a valid integer.")

    quantity = None
    try:
        quantity = float(data.get("quantity"))
        if quantity <= 0:
            errors.append("Quantity must be greater than 0.")
    except (TypeError, ValueError):
        errors.append("Quantity must be a valid number.")

    purchase_price = None
    try:
        purchase_price = float(data.get("purchase_price"))
        if purchase_price <= 0:
            errors.append("Purchase price must be greater than 0.")
    except (TypeError, ValueError):
        errors.append("Purchase price must be a valid number.")

    purchase_date = (data.get("purchase_date") or "").strip()
    try:
        datetime.datetime.strptime(purchase_date, "%Y-%m-%d")
    except ValueError:
        errors.append("Purchase date must be in YYYY-MM-DD format.")

    if errors:
        return False, errors

    created_at = datetime.datetime.today().strftime("%Y-%m-%d")

    conn = get_connection()
    c = conn.cursor()
    c.execute('''
              INSERT INTO investments (name, ticker, asset_type, category_id, quantity, purchase_price, purchase_date, created_at)
              VALUES (?, ?, ?, ?, ?, ?, ?, ?)
              ''', (name, ticker, asset_type, category_id, quantity, purchase_price, purchase_date, created_at))
    conn.commit()
    new_id = c.lastrowid
    conn.close()

    return True, {"id": new_id}


def get_all_investments():
    """Returns a list of dicts, one per investment, sorted by purchase_date desc."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT id, name, ticker, asset_type, category_id, quantity, purchase_price, purchase_date, created_at
              FROM investments
              ORDER BY purchase_date DESC
              """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_investment(investment_id):
    """Returns a single investment dict, or None if it doesn't exist."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT id, name, ticker, asset_type, category_id, quantity, purchase_price, purchase_date, created_at
              FROM investments WHERE id = ?
              """, (investment_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def filter_investments(mode="all", **kwargs):
    conn = get_connection()
    c = conn.cursor()

    query = """
            SELECT id, name, ticker, asset_type, category_id, quantity, purchase_price, purchase_date, created_at
            FROM investments \
            """
    params = []
    order_clause = ""

    if mode == "keyword":
        keyword = (kwargs.get("keyword") or "").strip()
        if not keyword:
            conn.close()
            return False, "Keyword cannot be empty."
        query += " WHERE name LIKE ? OR ticker LIKE ? OR asset_type LIKE ?"
        params = [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]

    elif mode == "type":
        asset_type = (kwargs.get("asset_type") or "").strip().title()
        if asset_type not in VALID_TYPES:
            conn.close()
            return False, f"'{asset_type}' is not a recognized type. Valid options: {', '.join(VALID_TYPES)}"
        query += " WHERE asset_type = ?"
        params = [asset_type]

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
        query += " WHERE purchase_date BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "range":
        range_option = kwargs.get("range_option")
        start_date, end_date = get_date_range(range_option)
        if start_date is None:
            conn.close()
            return False, "Invalid range option."
        query += " WHERE purchase_date BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "sort_date":
        order_clause = " ORDER BY purchase_date DESC"

    elif mode == "sort_value":
        query = """
                SELECT id, name, ticker, asset_type, category_id, quantity, purchase_price, purchase_date, created_at,
                       (quantity * purchase_price) AS total_value
                FROM investments
                ORDER BY total_value DESC \
                """

    elif mode == "all":
        order_clause = " ORDER BY purchase_date DESC"

    else:
        conn.close()
        return False, f"Unknown filter mode: {mode}"

    c.execute(query + order_clause, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return True, rows


def update_investment_field(investment_id, field, value):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM investments WHERE id = ?", (investment_id,))
    if c.fetchone() is None:
        conn.close()
        return False, "Investment does not exist."

    if field == "name":
        new_name = (value or "").strip()
        if not new_name:
            conn.close()
            return False, "Name cannot be empty."
        c.execute("UPDATE investments SET name = ? WHERE id = ?", (new_name, investment_id))

    elif field == "ticker":
        new_ticker = (value or "").strip().upper()
        if not new_ticker:
            conn.close()
            return False, "Ticker cannot be empty."
        c.execute("UPDATE investments SET ticker = ? WHERE id = ?", (new_ticker, investment_id))

    elif field == "asset_type":
        new_type = (value or "").strip().title()
        if new_type not in VALID_TYPES:
            conn.close()
            return False, f"Invalid asset type. Must be one of: {', '.join(VALID_TYPES)}"
        c.execute("UPDATE investments SET asset_type = ? WHERE id = ?", (new_type, investment_id))

    elif field == "category_id":
        try:
            category_id = int(value)
            if category_id <= 0 or not category_exists(category_id):
                conn.close()
                return False, "Category does not exist."
        except (TypeError, ValueError):
            conn.close()
            return False, "Category ID must be a valid integer."
        c.execute("UPDATE investments SET category_id = ? WHERE id = ?", (category_id, investment_id))

    elif field == "quantity":
        try:
            new_quantity = float(value)
            if new_quantity <= 0:
                conn.close()
                return False, "Quantity must be greater than 0."
        except (TypeError, ValueError):
            conn.close()
            return False, "Quantity must be a valid number."
        c.execute("UPDATE investments SET quantity = ? WHERE id = ?", (new_quantity, investment_id))

    elif field == "purchase_price":
        try:
            new_price = float(value)
            if new_price <= 0:
                conn.close()
                return False, "Purchase price must be greater than 0."
        except (TypeError, ValueError):
            conn.close()
            return False, "Purchase price must be a valid number."
        c.execute("UPDATE investments SET purchase_price = ? WHERE id = ?", (new_price, investment_id))

    elif field == "purchase_date":
        new_date = (value or "").strip()
        try:
            datetime.datetime.strptime(new_date, "%Y-%m-%d")
        except ValueError:
            conn.close()
            return False, "Purchase date must be in YYYY-MM-DD format."
        c.execute("UPDATE investments SET purchase_date = ? WHERE id = ?", (new_date, investment_id))

    else:
        conn.close()
        return False, f"Unknown field: {field}"

    conn.commit()
    conn.close()
    return True, None


def delete_investment(investment_id):
    """Returns (success: bool, error: str|None)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM investments WHERE id = ?", (investment_id,))
    if c.fetchone() is None:
        conn.close()
        return False, "Investment does not exist."
    c.execute("DELETE FROM investments WHERE id = ?", (investment_id,))
    conn.commit()
    conn.close()
    return True, None