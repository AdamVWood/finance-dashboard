"""Realistic sample data so the app can be explored before entering real data.

Run with ``flask --app run seed-demo`` (or from Settings when the database is
empty). Generates 12 months of activity ending today.
"""

import datetime as dt
import random

from .db import get_db
from .utils import add_months, month_start, today


def _cat(db, name, kind):
    row = db.execute("SELECT id FROM categories WHERE name = ? AND kind = ?", (name, kind)).fetchone()
    if row:
        return row["id"]
    return db.execute("INSERT INTO categories (name, kind) VALUES (?, ?)", (name, kind)).lastrowid


def seed_demo(months=12, seed=7):
    rng = random.Random(seed)
    db = get_db()
    end = today()
    start = add_months(month_start(end), -(months - 1))

    def account(name, type_, opening, institution=None):
        return db.execute(
            "INSERT INTO accounts (name, type, institution, opening_balance_cents, opened_on) VALUES (?,?,?,?,?)",
            (name, type_, institution, opening, start.isoformat()),
        ).lastrowid

    chequing = account("Everyday chequing", "checking", 185000, "Sample Bank")
    savings = account("High-interest savings", "savings", 3600000, "Sample Bank")
    cash = account("Wallet", "cash", 12000)
    card = account("Visa credit card", "credit_card", -64000, "Sample Bank")
    loan = account("Car loan", "loan", -1450000, "Sample Credit Union")

    c = {name: _cat(db, name, "expense") for name in [
        "Housing & rent", "Groceries", "Dining out", "Utilities", "Transportation", "Phone & internet",
        "Health & medical", "Insurance", "Entertainment", "Shopping", "Personal care", "Bank fees & charges",
        "Education", "Gifts & donations",
    ]}
    inc = {name: _cat(db, name, "income") for name in ["Salary", "Freelance & side income", "Interest & dividends"]}

    rows = []

    def txn(date, desc, type_, cents, acc, cat=None, to=None):
        if date > end:
            return
        rows.append((date.isoformat(), desc, type_, int(cents), acc, to, cat))

    month = start
    while month <= end:
        y, m = month.year, month.month
        d = lambda day: dt.date(y, m, min(day, 28))  # noqa: E731
        txn(d(25), "Monthly salary", "income", 520000, chequing, inc["Salary"])
        if rng.random() < 0.5:
            txn(d(rng.randint(5, 20)), "Web design project", "income", rng.choice([45000, 60000, 85000]),
                chequing, inc["Freelance & side income"])
        txn(d(28), "Savings interest", "income", rng.randint(900, 1400), savings, inc["Interest & dividends"])
        txn(d(1), "Apartment rent", "expense", 160000, chequing, c["Housing & rent"])
        txn(d(12), "Electricity bill", "expense", rng.randint(16000, 26000), chequing, c["Utilities"])
        txn(d(14), "Water bill", "expense", rng.randint(4500, 6500), chequing, c["Utilities"])
        txn(d(8), "Mobile & home internet", "expense", 21500, chequing, c["Phone & internet"])
        txn(d(3), "Car insurance", "expense", 18000, chequing, c["Insurance"])
        txn(d(28), "Monthly account fee", "expense", 1200, chequing, c["Bank fees & charges"])
        txn(d(15), "Car loan payment", "transfer", 42000, chequing, to=loan)
        txn(d(26), "Move to savings", "transfer", 60000, chequing, to=savings)
        txn(d(2), "Cash withdrawal", "transfer", 20000, chequing, to=cash)
        for week in range(4):
            txn(d(4 + week * 7), "Supermarket", "expense", rng.randint(14000, 23000), card, c["Groceries"])
            txn(d(2 + week * 7), "Fuel", "expense", rng.randint(7000, 11000), card, c["Transportation"])
            if rng.random() < 0.7:
                txn(d(6 + week * 7), rng.choice(["Lunch out", "Fish fry", "Coffee shop", "Takeaway dinner"]),
                    "expense", rng.randint(2500, 9000), rng.choice([card, cash]), c["Dining out"])
        txn(d(18), "Streaming subscriptions", "expense", 4600, card, c["Entertainment"])
        if rng.random() < 0.6:
            txn(d(rng.randint(9, 27)), rng.choice(["Cinema", "Concert tickets", "Beach day"]), "expense",
                rng.randint(4000, 15000), card, c["Entertainment"])
        if rng.random() < 0.55:
            txn(d(rng.randint(5, 27)), rng.choice(["Clothing", "Household items", "Electronics accessory"]),
                "expense", rng.randint(6000, 32000), card, c["Shopping"])
        if rng.random() < 0.35:
            txn(d(rng.randint(5, 27)), "Pharmacy", "expense", rng.randint(2500, 9000), cash, c["Health & medical"])
        txn(d(20), "Barber", "expense", 4000, cash, c["Personal care"])
        if m in (1, 9):
            txn(d(10), "Course textbooks", "expense", rng.randint(25000, 40000), card, c["Education"])
        if m == 12:
            txn(d(18), "Christmas gifts", "expense", 65000, card, c["Gifts & donations"])
        txn(d(22), "Credit card payment", "transfer", 150000, chequing, to=card)
        month = add_months(month, 1)

    db.executemany(
        """INSERT INTO transactions (date, description, type, amount_cents, account_id, to_account_id, category_id)
           VALUES (?,?,?,?,?,?,?)""",
        rows,
    )

    # Budgets for the last three months.
    plan = {"Housing & rent": 160000, "Groceries": 75000, "Dining out": 20000, "Utilities": 30000,
            "Transportation": 38000, "Phone & internet": 21500, "Entertainment": 10000, "Shopping": 15000,
            "Insurance": 18000, "Personal care": 5000}
    for i in range(3):
        bm = add_months(month_start(end), -i)
        for name, cents in plan.items():
            db.execute("INSERT OR IGNORE INTO budgets (category_id, year, month, amount_cents) VALUES (?,?,?,?)",
                       (c[name], bm.year, bm.month, cents))

    # Savings goals with contribution history.
    def goal(name, target, deadline, monthly, initial):
        gid = db.execute(
            "INSERT INTO savings_goals (name, target_cents, start_date, deadline) VALUES (?,?,?,?)",
            (name, target, start.isoformat(), deadline.isoformat() if deadline else None),
        ).lastrowid
        if initial:
            db.execute("INSERT INTO goal_contributions (goal_id, date, amount_cents, note) VALUES (?,?,?,?)",
                       (gid, start.isoformat(), initial, "Starting balance"))
        cm = add_months(start, 1)
        while cm.replace(day=26) <= end:
            db.execute("INSERT INTO goal_contributions (goal_id, date, amount_cents) VALUES (?,?,?)",
                       (gid, cm.replace(day=26).isoformat(), monthly))
            cm = add_months(cm, 1)

    goal("Emergency fund", 1500000, add_months(end, 14), 35000, 400000)
    goal("New laptop", 350000, add_months(end, 2), 15000, 50000)
    goal("Trip to Toronto", 600000, None, 10000, 0)

    # Investments with monthly price history.
    holdings = [
        ("Vanguard Total World ETF", "VT", "etf", 40, 205.0, 0.011),
        ("S&P 500 index ETF", "VOO", "etf", 8, 880.0, 0.012),
        ("Local blue-chip shares", "BLUE", "stock", 500, 4.20, 0.004),
        ("Government savings bond", None, "bond", 1, 5000.0, 0.003),
        ("Bitcoin", "BTC", "crypto", 0.05, 120000.0, 0.03),
    ]
    for name, ticker, kind, qty, price, drift in holdings:
        bought = add_months(start, rng.randint(0, 3))
        hid = db.execute(
            """INSERT INTO investments (name, ticker, asset_type, quantity, purchase_price, purchase_date,
                                       funding_account_id)
               VALUES (?,?,?,?,?,?,?)""",
            (name, ticker, kind, qty, price, bought.isoformat(), savings),
        ).lastrowid
        p, pm = price, bought
        while pm <= end:
            db.execute("INSERT OR IGNORE INTO investment_prices (investment_id, date, price) VALUES (?,?,?)",
                       (hid, pm.isoformat(), round(p, 4)))
            p *= 1 + drift + rng.uniform(-0.05, 0.05) * (3 if kind == "crypto" else 1)
            pm = add_months(pm, 1)
        db.execute("UPDATE investments SET current_price = ?, price_date = ? WHERE id = ?",
                   (round(p, 4), end.isoformat(), hid))
        db.execute("INSERT OR REPLACE INTO investment_prices (investment_id, date, price) VALUES (?,?,?)",
                   (hid, end.isoformat(), round(p, 4)))

    # Recurring items, scheduled from next month so nothing is double-posted.
    nm = add_months(month_start(end), 1)
    for desc, type_, cents, acc, cat, to, day in [
        ("Monthly salary", "income", 520000, chequing, inc["Salary"], None, 25),
        ("Apartment rent", "expense", 160000, chequing, c["Housing & rent"], None, 1),
        ("Mobile & home internet", "expense", 21500, chequing, c["Phone & internet"], None, 8),
        ("Car loan payment", "transfer", 42000, chequing, None, loan, 15),
        ("Move to savings", "transfer", 60000, chequing, None, savings, 26),
    ]:
        first = nm.replace(day=day).isoformat()
        db.execute(
            """INSERT INTO recurring (description, type, amount_cents, account_id, to_account_id, category_id,
                                      frequency, start_date, next_date) VALUES (?,?,?,?,?,?,'monthly',?,?)""",
            (desc, type_, cents, acc, to, cat, first, first),
        )
    db.commit()
