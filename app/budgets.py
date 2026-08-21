import datetime
from app.categories import category_exists
from database.database import get_connection


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


def add_budget(data):
    errors = []

    amount = None
    try:
        amount = float(data.get("amount"))
        if amount <= 0:
            errors.append("Amount must be greater than 0.")
    except (TypeError, ValueError):
        errors.append("Amount must be a valid number.")

    category_id = None
    try:
        category_id = int(data.get("category_id"))
        if category_id <= 0:
            errors.append("Category ID must be a positive integer.")
        elif not category_exists(category_id):
            errors.append("Category does not exist.")
    except (TypeError, ValueError):
        errors.append("Category ID must be a valid integer.")

    month = None
    try:
        month = int(data.get("month"))
        if not (1 <= month <= 12):
            errors.append("Month must be between 1 and 12.")
    except (TypeError, ValueError):
        errors.append("Month must be a valid number.")

    year = None
    try:
        year = int(data.get("year"))
        if not (1990 <= year <= 2100):
            errors.append("Year must be a valid four-digit year.")
    except (TypeError, ValueError):
        errors.append("Year must be a valid number.")

    if errors:
        return False, errors

    conn = get_connection()
    c = conn.cursor()

    c.execute(
        "SELECT id FROM budgets WHERE category_id = ? AND month = ? AND year = ?",
        (category_id, month, year),
    )
    if c.fetchone():
        conn.close()
        return False, ["A budget for this category and period already exists."]

    created_at = datetime.datetime.today().strftime("%Y-%m-%d")
    c.execute(
        """INSERT INTO budgets (category_id, amount, month, year, created_at)
           VALUES (?, ?, ?, ?, ?)""",
        (category_id, amount, month, year, created_at),
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return True, {"id": new_id}


def get_all_budgets():
    """Returns a list of dicts, one per budget, sorted by year/month desc."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT b.id, b.category_id, c.name AS category_name, b.amount, b.month, b.year, b.created_at
              FROM budgets b
                       INNER JOIN categories c ON b.category_id = c.id
              ORDER BY b.year DESC, b.month DESC
              """)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return rows


def get_budget(budget_id):
    """Returns a single budget dict, or None if it doesn't exist."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT b.id, b.category_id, c.name AS category_name, b.amount, b.month, b.year, b.created_at
              FROM budgets b
                       INNER JOIN categories c ON b.category_id = c.id
              WHERE b.id = ?
              """, (budget_id,))
    row = c.fetchone()
    conn.close()
    return dict(row) if row else None


def filter_budgets(mode="all", **kwargs):
    conn = get_connection()
    c = conn.cursor()

    query = """
            SELECT b.id, b.category_id, c.name AS category_name, b.amount, b.month, b.year, b.created_at
            FROM budgets b
                     INNER JOIN categories c ON b.category_id = c.id \
            """
    params = []
    order_clause = ""

    if mode == "keyword":
        keyword = (kwargs.get("keyword") or "").strip()
        if not keyword:
            conn.close()
            return False, "Keyword cannot be empty."
        query += " WHERE c.name LIKE ? OR b.month LIKE ? OR b.year LIKE ?"
        params = [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]

    elif mode == "category":
        category = (kwargs.get("category") or "").strip()
        if not category:
            conn.close()
            return False, "Category cannot be empty."
        query += " WHERE c.name = ?"
        params = [category]

    elif mode == "range":
        range_option = kwargs.get("range_option")
        start_date, end_date = get_date_range(range_option)
        if start_date is None:
            conn.close()
            return False, "Invalid range option."
        query += " WHERE b.created_at BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "month_year":
        try:
            month = int(kwargs.get("month"))
            year = int(kwargs.get("year"))
            if not (1 <= month <= 12):
                conn.close()
                return False, "Month must be between 1 and 12."
        except (TypeError, ValueError):
            conn.close()
            return False, "Month and year must be numbers."
        query += " WHERE b.month = ? AND b.year = ?"
        params = [month, year]

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
        query += " WHERE b.created_at BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "sort_date":
        order_clause = " ORDER BY b.created_at DESC"

    elif mode == "sort_amount":
        order_clause = " ORDER BY b.amount DESC"

    elif mode == "all":
        order_clause = " ORDER BY b.year DESC, b.month DESC"

    else:
        conn.close()
        return False, f"Unknown filter mode: {mode}"

    c.execute(query + order_clause, params)
    rows = [dict(r) for r in c.fetchall()]
    conn.close()
    return True, rows


def update_budget_field(budget_id, field, value, value2=None):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM budgets WHERE id = ?", (budget_id,))
    if c.fetchone() is None:
        conn.close()
        return False, "Budget does not exist."

    if field == "category_id":
        try:
            category_id = int(value)
            if category_id <= 0 or not category_exists(category_id):
                conn.close()
                return False, "Category does not exist."
        except (TypeError, ValueError):
            conn.close()
            return False, "Category ID must be a valid integer."
        c.execute("UPDATE budgets SET category_id = ? WHERE id = ?", (category_id, budget_id))

    elif field == "amount":
        try:
            new_amount = float(value)
            if new_amount <= 0:
                conn.close()
                return False, "New amount must be greater than 0."
        except (TypeError, ValueError):
            conn.close()
            return False, "Invalid amount. Please enter a number."
        c.execute("UPDATE budgets SET amount = ? WHERE id = ?", (new_amount, budget_id))

    elif field == "period":
        try:
            month = int(value)
            year = int(value2)
            if not (1 <= month <= 12):
                conn.close()
                return False, "Month must be between 1 and 12."
            if not (1990 <= year <= 2100):
                conn.close()
                return False, "Year must be a valid four-digit year."
        except (TypeError, ValueError):
            conn.close()
            return False, "Invalid month or year."
        c.execute("UPDATE budgets SET month = ?, year = ? WHERE id = ?", (month, year, budget_id))

    else:
        conn.close()
        return False, f"Unknown field: {field}"

    conn.commit()
    conn.close()
    return True, None


def delete_budget(budget_id):
    """Returns (success: bool, error: str|None)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM budgets WHERE id = ?", (budget_id,))
    if c.fetchone() is None:
        conn.close()
        return False, "Budget does not exist."
    c.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
    conn.commit()
    conn.close()
    return True, None


def budget_dashboard():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT b.id, b.category_id, c.name, b.amount, b.month, b.year
              FROM budgets b
                       INNER JOIN categories c ON b.category_id = c.id
              """)
    budgets = c.fetchall()

    total_budget = 0.0
    total_spent = 0.0
    over_budget = []
    near_limit = []
    categories = []

    for bid, cat_id, cat_name, amount, month, year in budgets:
        amount = float(amount or 0)
        total_budget += amount

        c.execute("""
                  SELECT SUM(amount) FROM transactions
                  WHERE category_id = ? AND transaction_type = 'Expense'
                    AND strftime('%m', date) = ? AND strftime('%Y', date) = ?
                  """, (cat_id, f"{month:02d}", str(year)))
        spent = c.fetchone()[0]
        spent = float(spent or 0)
        total_spent += spent

        progress = (spent / amount * 100) if amount > 0 else 0
        if progress > 100:
            over_budget.append(cat_name)
            state = "Over budget"
        elif progress >= 80:
            near_limit.append(cat_name)
            state = "Near limit"
        else:
            state = "Under budget"

        categories.append({
            "id": bid,
            "category_name": cat_name,
            "amount": amount,
            "spent": spent,
            "progress": progress,
            "status": state,
        })

    remaining = total_budget - total_spent
    percent_used = (total_spent / total_budget) * 100 if total_budget > 0 else 0

    conn.close()

    return {
        "categories": categories,
        "total_budget": total_budget,
        "total_spent": total_spent,
        "remaining": remaining,
        "percent_used": percent_used,
        "over_budget": over_budget,
        "near_limit": near_limit,
    }


def budget_summary():
    """Returns a dict: {total_budget, total_spent, remaining, percent_used}."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM budgets")
    total_budget = float(c.fetchone()[0] or 0)

    c.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'Expense'")
    total_spent = float(c.fetchone()[0] or 0)

    remaining = total_budget - total_spent
    percent_used = (total_spent / total_budget * 100) if total_budget > 0 else 0

    conn.close()

    return {
        "total_budget": total_budget,
        "total_spent": total_spent,
        "remaining": remaining,
        "percent_used": percent_used,
    }