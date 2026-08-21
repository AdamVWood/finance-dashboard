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


def _with_progress(goal):
    """Adds computed progress/remaining/required_monthly/status fields to a goal dict."""
    target = float(goal.get("target_amount") or 0)
    current = float(goal.get("current_amount") or 0)
    deadline = goal.get("deadline")

    progress = (current / target * 100) if target > 0 else 0
    remaining = target - current

    required_monthly = 0
    months_left = None
    if deadline:
        try:
            deadline_date = datetime.datetime.strptime(deadline, "%Y-%m-%d")
            months_left = max(
                1,
                (deadline_date.year - datetime.date.today().year) * 12
                + (deadline_date.month - datetime.date.today().month),
                )
            required_monthly = remaining / months_left if remaining > 0 else 0
        except ValueError:
            pass

    status = "On track" if progress >= (100 * (datetime.date.today().month / 12)) else "Behind schedule"

    goal = dict(goal)
    goal["target_amount"] = target
    goal["current_amount"] = current
    goal["progress"] = progress
    goal["remaining"] = remaining
    goal["required_monthly"] = required_monthly
    goal["months_left"] = months_left
    goal["status"] = status
    return goal


def add_savings_goal(data):
    errors = []

    name = (data.get("name") or "").strip()
    if not name:
        errors.append("Name cannot be empty.")

    category_id = None
    try:
        category_id = int(data.get("category_id"))
        if category_id <= 0:
            errors.append("Category ID must be a positive integer.")
        elif not category_exists(category_id):
            errors.append("Category does not exist.")
    except (TypeError, ValueError):
        errors.append("Category ID must be a valid integer.")

    target_amount = None
    try:
        target_amount = float(data.get("target_amount"))
        if target_amount <= 0:
            errors.append("Target amount must be greater than 0.")
    except (TypeError, ValueError):
        errors.append("Target amount must be a valid number.")

    current_amount = None
    try:
        current_amount = float(data.get("current_amount", 0) or 0)
        if current_amount < 0:
            errors.append("Current amount cannot be negative.")
    except (TypeError, ValueError):
        errors.append("Current amount must be a valid number.")

    deadline = (data.get("deadline") or "").strip()
    try:
        datetime.datetime.strptime(deadline, "%Y-%m-%d")
    except ValueError:
        errors.append("Deadline must be in YYYY-MM-DD format.")

    if errors:
        return False, errors

    created_at = datetime.datetime.today().strftime("%Y-%m-%d")

    conn = get_connection()
    c = conn.cursor()
    c.execute(
        """INSERT INTO savings_goals (name, category_id, target_amount, current_amount, deadline, created_at)
           VALUES (?, ?, ?, ?, ?, ?)""",
        (name, category_id, target_amount, current_amount, deadline, created_at),
    )
    conn.commit()
    new_id = c.lastrowid
    conn.close()
    return True, {"id": new_id}


def get_all_savings_goals():
    """Returns a list of dicts (with computed progress fields), sorted by deadline asc."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT id, name, category_id, target_amount, current_amount, deadline, created_at
              FROM savings_goals
              ORDER BY deadline ASC
              """)
    rows = [_with_progress(dict(r)) for r in c.fetchall()]
    conn.close()
    return rows


def get_savings_goal(goal_id):
    """Returns a single savings goal dict (with computed progress fields), or None."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT id, name, category_id, target_amount, current_amount, deadline, created_at
              FROM savings_goals WHERE id = ?
              """, (goal_id,))
    row = c.fetchone()
    conn.close()
    return _with_progress(dict(row)) if row else None


def filter_savings_goals(mode="all", **kwargs):
    conn = get_connection()
    c = conn.cursor()

    query = """
            SELECT id, name, category_id, target_amount, current_amount, deadline, created_at
            FROM savings_goals \
            """
    params = []
    order_clause = ""

    if mode == "keyword":
        keyword = (kwargs.get("keyword") or "").strip()
        if not keyword:
            conn.close()
            return False, "Keyword cannot be empty."
        query += " WHERE name LIKE ?"
        params = [f"%{keyword}%"]

    elif mode == "range":
        range_option = kwargs.get("range_option")
        start_date, end_date = get_date_range(range_option)
        if start_date is None:
            conn.close()
            return False, "Invalid range option."
        query += " WHERE deadline BETWEEN ? AND ?"
        params = [start_date, end_date]

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
        query += " WHERE deadline BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "sort_deadline":
        order_clause = " ORDER BY deadline ASC"

    elif mode == "sort_target":
        order_clause = " ORDER BY target_amount DESC"

    elif mode == "sort_current":
        order_clause = " ORDER BY current_amount DESC"

    elif mode == "all":
        order_clause = " ORDER BY deadline ASC"

    else:
        conn.close()
        return False, f"Unknown filter mode: {mode}"

    c.execute(query + order_clause, params)
    rows = [_with_progress(dict(r)) for r in c.fetchall()]
    conn.close()
    return True, rows


def add_money_to_goal(goal_id, amount):
    conn = get_connection()
    c = conn.cursor()
    c.execute(
        "SELECT target_amount, current_amount, deadline FROM savings_goals WHERE id = ?",
        (goal_id,),
    )
    goal = c.fetchone()
    if not goal:
        conn.close()
        return False, "Savings goal not found."

    try:
        add_amount = float(amount)
        if add_amount <= 0:
            conn.close()
            return False, "Amount must be greater than 0."
    except (TypeError, ValueError):
        conn.close()
        return False, "Invalid input."

    current = float(goal["current_amount"] or 0)
    new_current = current + add_amount
    c.execute("UPDATE savings_goals SET current_amount = ? WHERE id = ?", (new_current, goal_id))
    conn.commit()
    conn.close()

    return True, get_savings_goal(goal_id)


def update_savings_goal_field(goal_id, field, value):
    conn = get_connection()
    c = conn.cursor()

    c.execute("SELECT id FROM savings_goals WHERE id = ?", (goal_id,))
    if c.fetchone() is None:
        conn.close()
        return False, "Savings goal does not exist."

    if field == "name":
        new_name = (value or "").strip()
        if not new_name:
            conn.close()
            return False, "Name cannot be empty."
        c.execute("UPDATE savings_goals SET name = ? WHERE id = ?", (new_name, goal_id))

    elif field == "target_amount":
        try:
            new_target = float(value)
            if new_target <= 0:
                conn.close()
                return False, "Target amount must be greater than 0."
        except (TypeError, ValueError):
            conn.close()
            return False, "Target amount must be a valid number."
        c.execute("UPDATE savings_goals SET target_amount = ? WHERE id = ?", (new_target, goal_id))

    elif field == "current_amount":
        try:
            new_current = float(value)
            if new_current < 0:
                conn.close()
                return False, "Current amount cannot be negative."
        except (TypeError, ValueError):
            conn.close()
            return False, "Current amount must be a valid number."
        c.execute("UPDATE savings_goals SET current_amount = ? WHERE id = ?", (new_current, goal_id))

    elif field == "deadline":
        new_deadline = (value or "").strip()
        try:
            datetime.datetime.strptime(new_deadline, "%Y-%m-%d")
        except ValueError:
            conn.close()
            return False, "Deadline must be in YYYY-MM-DD format."
        c.execute("UPDATE savings_goals SET deadline = ? WHERE id = ?", (new_deadline, goal_id))

    elif field == "category_id":
        try:
            new_cat = int(value)
            if new_cat <= 0 or not category_exists(new_cat):
                conn.close()
                return False, "Category does not exist."
        except (TypeError, ValueError):
            conn.close()
            return False, "Category ID must be a valid integer."
        c.execute("UPDATE savings_goals SET category_id = ? WHERE id = ?", (new_cat, goal_id))

    else:
        conn.close()
        return False, f"Unknown field: {field}"

    conn.commit()
    conn.close()
    return True, None


def delete_savings_goal(goal_id):
    """Returns (success: bool, error: str|None)."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT id FROM savings_goals WHERE id = ?", (goal_id,))
    if c.fetchone() is None:
        conn.close()
        return False, "Savings goal does not exist."
    c.execute("DELETE FROM savings_goals WHERE id = ?", (goal_id,))
    conn.commit()
    conn.close()
    return True, None