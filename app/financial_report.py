import sqlite3


def report_income_expenses():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'Deposit'")
    income = c.fetchone()[0] or 0
    c.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'Withdrawal'")
    expenses = c.fetchone()[0] or 0
    balance = income - expenses
    print("\n==== Income vs Expenses ====\n")
    print(f"Total Income: {income:.2f}")
    print(f"Total Expenses: {expenses:.2f}")
    print(f"Current Balance: {balance:.2f}")
    conn.close()


def report_spending_by_category():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT c.name, SUM(t.amount)
        FROM transactions t
        INNER JOIN categories c ON t.category_id = c.id
        WHERE t.transaction_type = 'Withdrawal'
        GROUP BY c.name
    """)
    rows = c.fetchall()
    print("\n==== Spending by Category ====\n")
    for row in rows:
        print(f"{row[0]:<15} {row[1]:.2f}")
    conn.close()


def report_budget_vs_actual(month, year):
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT c.name, b.amount, IFNULL(SUM(t.amount),0)
        FROM budgets b
        INNER JOIN categories c ON b.category_id = c.id
        LEFT JOIN transactions t ON b.category_id = t.category_id AND strftime('%m', t.date) = ? AND strftime('%Y', t.date) = ?
        GROUP BY c.name, b.amount
    """, (f"{month:02d}", str(year)))
    rows = c.fetchall()
    print(f"\n==== Budget vs Actual ({month}/{year}) ====\n")
    for row in rows:
        print(f"{row[0]:<15} Budget: {row[1]:.2f} | Actual: {row[2]:.2f}")
    conn.close()


def report_savings_goals():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT g.name, c.name, g.target_amount, g.current_amount, g.deadline
        FROM savings_goals g
        INNER JOIN categories c ON g.category_id = c.id
    """)
    rows = c.fetchall()
    print("\n==== Savings Goals Progress ====\n")
    for row in rows:
        progress = (row[2] and row[3]) and (row[3] / row[2] * 100) or 0
        print(
            f"{str(row[0]):<20} ({str(row[1]):<15}) "
            f"Target: {float(row[2] or 0):.2f} | "
            f"Current: {float(row[3] or 0):.2f} | "
            f"Progress: {float(progress or 0):.1f}% | "
            f"Deadline: {row[4]}"
        )

    conn.close()


def report_investments():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT i.name, i.ticker, c.name, i.quantity, i.purchase_price, i.purchase_date
        FROM investments i
        INNER JOIN categories c ON i.category_id = c.id
    """)
    rows = c.fetchall()
    print("\n==== Investments Overview ====\n")
    for row in rows:
        total_value = row[3] * row[4]
        print(f"{row[0]:<20} ({row[1]:<10}) Category: {row[2]:<15} Qty: {row[3]:.2f} Price: {row[4]:.2f} Total Value: {total_value:.2f} Date: {row[5]}")
    conn.close()

