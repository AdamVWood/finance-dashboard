from database.database import get_connection


def report_portfolio_overview():
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT name, ticker, quantity, purchase_price, purchase_date
              FROM investments
              """)
    rows = c.fetchall()
    conn.close()

    holdings = []
    total_invested = 0.0
    total_value = 0.0

    for row in rows:
        qty = float(row["quantity"] or 0)
        price = float(row["purchase_price"] or 0)
        invested = qty * price
        total_invested += invested
        total_value += invested  # later replace with live market value if available
        holdings.append({
            "name": row["name"],
            "ticker": row["ticker"],
            "quantity": qty,
            "price": price,
            "total_value": invested,
            "date": row["purchase_date"],
        })

    profit_loss = total_value - total_invested
    return_pct = (profit_loss / total_invested * 100) if total_invested > 0 else 0

    return {
        "holdings": holdings,
        "total_invested": total_invested,
        "total_value": total_value,
        "profit_loss": profit_loss,
        "return_pct": return_pct,
        "num_holdings": len(holdings),
    }


def report_budget_dashboard(month, year):
    """Returns a dict: {total_budget, total_spent, remaining, pct_used, month, year}."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT SUM(b.amount), IFNULL(SUM(t.amount),0)
              FROM budgets b
                       LEFT JOIN transactions t
                                 ON b.category_id = t.category_id
                                     AND strftime('%m', t.date) = ? AND strftime('%Y', t.date) = ?
              """, (f"{month:02d}", str(year)))
    totals = c.fetchone()
    conn.close()

    total_budget = totals[0] or 0
    total_spent = totals[1] or 0
    remaining = total_budget - total_spent
    pct_used = (total_spent / total_budget * 100) if total_budget > 0 else 0

    return {
        "total_budget": total_budget,
        "total_spent": total_spent,
        "remaining": remaining,
        "pct_used": pct_used,
        "month": month,
        "year": year,
    }


def report_savings_goals_insights():
    """Returns a list of dicts: {name, target, current, remaining, pct_complete, deadline}."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT name, target_amount, current_amount, deadline
              FROM savings_goals
              """)
    rows = c.fetchall()
    conn.close()

    results = []
    for row in rows:
        target = float(row["target_amount"] or 0)
        current = float(row["current_amount"] or 0)
        remaining = target - current
        pct_complete = (current / target * 100) if target > 0 else 0
        results.append({
            "name": row["name"],
            "target": target,
            "current": current,
            "remaining": remaining,
            "pct_complete": pct_complete,
            "deadline": row["deadline"],
        })
    return results


def report_monthly_income_expenses(year):
    """Returns a list of dicts: {month, income, expenses}."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT strftime('%m', date) AS month,
               SUM(CASE WHEN transaction_type='Deposit' THEN amount ELSE 0 END) AS income,
               SUM(CASE WHEN transaction_type='Withdrawal' THEN amount ELSE 0 END) AS expenses
              FROM transactions
              WHERE strftime('%Y', date) = ?
              GROUP BY month
              ORDER BY month
              """, (str(year),))
    rows = c.fetchall()
    conn.close()

    return [
        {"month": row["month"], "income": row["income"] or 0, "expenses": row["expenses"] or 0}
        for row in rows
    ]


def report_income_expenses():
    """Returns a dict: {income, expenses, balance}."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'Deposit'")
    income = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'Withdrawal'")
    expenses = c.fetchone()[0] or 0
    conn.close()

    return {"income": income, "expenses": expenses, "balance": income - expenses}


def report_spending_by_category():
    """Returns a list of dicts: {category, total}."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT c.name, SUM(t.amount)
              FROM transactions t
                       INNER JOIN categories c ON t.category_id = c.id
              WHERE t.transaction_type = 'Withdrawal'
              GROUP BY c.name
              """)
    rows = c.fetchall()
    conn.close()
    return [{"category": row[0], "total": row[1]} for row in rows]


def report_budget_vs_actual(month, year):
    """Returns a list of dicts: {category, budget, actual}."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT c.name, b.amount, IFNULL(SUM(t.amount),0)
              FROM budgets b
                       INNER JOIN categories c ON b.category_id = c.id
                       LEFT JOIN transactions t ON b.category_id = t.category_id AND strftime('%m', t.date) = ? AND strftime('%Y', t.date) = ?
              GROUP BY c.name, b.amount
              """, (f"{month:02d}", str(year)))
    rows = c.fetchall()
    conn.close()
    return [{"category": row[0], "budget": row[1], "actual": row[2]} for row in rows]


def report_savings_goals():
    """Returns a list of dicts: {name, category, target, current, progress, deadline}."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT g.name, c.name, g.target_amount, g.current_amount, g.deadline
              FROM savings_goals g
                       INNER JOIN categories c ON g.category_id = c.id
              """)
    rows = c.fetchall()
    conn.close()

    results = []
    for row in rows:
        target = float(row[2] or 0)
        current = float(row[3] or 0)
        progress = (current / target * 100) if target > 0 else 0
        results.append({
            "name": row[0],
            "category": row[1],
            "target": target,
            "current": current,
            "progress": progress,
            "deadline": row[4],
        })
    return results


def report_investments():
    """Returns a list of dicts: {name, ticker, category, quantity, price, total_value, date}."""
    conn = get_connection()
    c = conn.cursor()
    c.execute("""
              SELECT i.name, i.ticker, c.name, i.quantity, i.purchase_price, i.purchase_date
              FROM investments i
                       INNER JOIN categories c ON i.category_id = c.id
              """)
    rows = c.fetchall()
    conn.close()

    results = []
    for row in rows:
        qty = float(row[3] or 0)
        price = float(row[4] or 0)
        results.append({
            "name": row[0],
            "ticker": row[1],
            "category": row[2],
            "quantity": qty,
            "price": price,
            "total_value": qty * price,
            "date": row[5],
        })
    return results