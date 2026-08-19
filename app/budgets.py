import sqlite3
import datetime
from app.categories import category_exists


def budget_dashboard():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    # Get all budgets with category names
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

    for bid, cat_id, cat_name, amount, month, year in budgets:
        amount = float(amount or 0)
        total_budget += amount

        # Sum transactions for this category/month/year
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

        # Print per‑category progress bar
        bar_length = 20
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)

        print(f"\n{cat_name}")
        print(f"${spent:.2f} / ${amount:.2f}")
        print(f"{bar} {progress:.0f}%")
        print(f"Status: {state}")

    remaining = total_budget - total_spent
    percent_used = (total_spent / total_budget) * 100 if total_budget > 0 else 0

    print("\n==== Budget Dashboard ====")
    print(f"Total Budget: ${total_budget:.2f}")
    print(f"Total Spent: ${total_spent:.2f}")
    print(f"Remaining: ${remaining:.2f}")
    print(f"Percentage Used: {percent_used:.0f}%")
    print(f"Categories Over Budget: {', '.join(over_budget) if over_budget else 'None'}")
    print(f"Categories Near Limit: {', '.join(near_limit) if near_limit else 'None'}")

    conn.close()


def budget_summary():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("SELECT SUM(amount) FROM budgets")
    total_budget = float(c.fetchone()[0] or 0)

    c.execute("SELECT SUM(amount) FROM transactions WHERE transaction_type = 'Expense'")
    total_spent = float(c.fetchone()[0] or 0)

    remaining = total_budget - total_spent
    percent_used = (total_spent / total_budget * 100) if total_budget > 0 else 0

    print("\n==== Quick Budget Summary ====")
    print(f"Total Budget: ${total_budget:.2f}")
    print(f"Total Spent: ${total_spent:.2f}")
    print(f"Remaining: ${remaining:.2f}")
    print(f"Percentage Used: {percent_used:.0f}%")

    conn.close()


def add_budget():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    # Amount: must be a positive number
    while True:
        try:
            amount = float(input("Please enter your amount: "))
            if amount <= 0:
                print("Amount must be greater than 0.")
                continue
            break
        except ValueError:
            print("Invalid amount. Please enter a number.")

    # Category: cannot be empty
    while True:
        try:
            category = int(input("Please enter the category ID: "))
            if category > 0:
                # Check if category exists first
                c.execute("SELECT id FROM categories WHERE id = ?", (category,))
                if c.fetchone():
                    break  # valid category, exit loop
                else:
                    print("Category does not exist.")
            else:
                print("Category ID must be a positive integer.")
        except ValueError:
            print("Please enter a valid category ID.")

    # Month: 1-12
    while True:
        try:
            month = int(input("Please enter the month (1-12): "))
            if 1 <= month <= 12:
                break
            else:
                print("Month must be between 1 and 12.")
        except ValueError:
            print("Invalid input. Please enter a valid month.")

    #Year: four digits
    while True:
        try:
            year = int(input("Please enter the year (YYYY): "))
            if 1990 <= year <= 2100:
                break
            else:
                print("Year must be a valid four-digit year.")
        except ValueError:
            print("Invalid input. Please enter a valid year.")

    created_at = datetime.datetime.today().strftime("%Y-%m-%d")
    c.execute("SELECT id FROM budgets WHERE category_id = ? AND month = ? AND year = ?", (category, month, year))
    if c.fetchone():
        print("A budget for this category and period already exists.")
        conn.close()
        return

    c.execute('''
        INSERT INTO budgets (category_id, amount, month, year, created_at)
        VALUES (?, ?, ?, ?)
        ''', (category, amount, month, year, created_at))  # enters the data
    conn.commit()
    conn.close()


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


def filter_budgets(mode="all"):
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    query = """
        SELECT b.id, b.amount, c.name, b.month, b.year, b.created_at
        FROM budgets b
        INNER JOIN categories c ON b.category_id = c.id
    """
    params = []
    order_clause = ""

    if mode == "keyword":
        keyword = input("Enter keyword (category/month/year): ").strip()
        if not keyword:
            print("Error: Keyword cannot be empty.")
            conn.close()
            return
        query += " WHERE c.name LIKE ? OR b.month LIKE ? OR b.year LIKE ?"
        params = [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]

    elif mode == "category":
        category = input("Enter category name: ").strip()
        if not category:
            print("Error: Category cannot be empty.")
            conn.close()
            return
        query += " WHERE c.name = ?"
        params = [category]

    elif mode == "range":
        print("\nSelect a date range:")
        print("1: This Month")
        print("2: Last Month")
        print("3: Last 3 Months")
        print("4: This Year")
        print("5: All Time")

        choice = input("Enter choice: ").strip()
        ranges = {
            "1": "this_month",
            "2": "last_month",
            "3": "last_3_months",
            "4": "this_year",
            "5": "all_time"
        }

        if choice not in ranges:
            print("Invalid choice.")
            conn.close()
            return

        start_date, end_date = get_date_range(ranges[choice])
        query += " WHERE b.created_at BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "month_year":
        try:
            month = int(input("Enter month (1–12): ").strip())
            year = int(input("Enter year (YYYY): ").strip())
            if month < 1 or month > 12:
                print("Error: Month must be between 1 and 12.")
                conn.close()
                return
        except ValueError:
            print("Error: Month and year must be numbers.")
            conn.close()
            return
        query += " WHERE b.month = ? AND b.year = ?"
        params = [month, year]

    elif mode == "date":
        start_date = input("Enter start date (YYYY-MM-DD): ").strip()
        end_date = input("Enter end date (YYYY-MM-DD): ").strip()
        try:
            start_dt = datetime.datetime.strptime(start_date, "%Y-%m-%d")
            end_dt = datetime.datetime.strptime(end_date, "%Y-%m-%d")
            if start_dt > end_dt:
                print("Error: Start date cannot be after end date.")
                conn.close()
                return
        except ValueError:
            print("Error: Dates must be in YYYY-MM-DD format.")
            conn.close()
            return
        query += " WHERE b.created_at BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "sort_date":
        order_clause = " ORDER BY b.created_at DESC"

    elif mode == "sort_amount":
        order_clause = " ORDER BY b.amount DESC"

    elif mode == "all":
        order_clause = " ORDER BY b.year DESC, b.month DESC"

    # Execute query
    c.execute(query + order_clause, params)
    rows = c.fetchall()

    if not rows:
        print("No matching budgets found.")
    else:
        print("\n==== Budgets ====\n")
        print(f"{'ID':<5} {'Amount':>12} {'Category':<15} {'Month':<8} {'Year':<6} {'Created At':<12}")
        print("-" * 70)
        for row in rows:
            bid = row[0]
            amount = f"${row[1]:,.2f}"
            category = row[2]
            month = row[3]
            year = row[4]
            created_at = row[5][:10]
            print(f"{bid:<5} {amount:>12} {category:<15} {month:<8} {year:<6} {created_at:<12}")

    conn.close()


def view_budgets():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT b.id, c.name, b.amount, b.month, b.year, b.created_at
        FROM budgets b
        INNER JOIN categories c ON b.category_id = c.id
    """)
    rows = c.fetchall()

    if not rows:
        print("No budgets found.")
    else:
        print("\n==== Budgets Overview ====\n")
        # Print headers
        print(f"{'ID':<5} {'Amount':>12} {'Category':<15} {'Month':<8} {'Year':<6} {'Created At':<12}")
        print("-" * 70)
        # Print each budget row
        for row in rows:
            bid = row[0]
            amount = f"${row[2]:,.2f}"
            category = row[1]
            month = row[3]
            year = row[4]
            created_at = row[5][:10]  # slice to YYYY-MM-DD
            print(f"{bid:<5} {amount:>12} {category:<15} {month:<8} {year:<6} {created_at:<12}")

    conn.close()


def delete_budget():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    # Check if there are any budgets
    c.execute("SELECT COUNT(*) FROM budgets")
    if c.fetchone()[0] == 0:
        print("There are no budgets.")
        conn.close()
        return

    # Ask for ID and validate
    while True:
        try:
            budget_id = int(input("Enter the ID of the budget you want to delete: "))
            c.execute("SELECT id FROM budgets WHERE id = ?", (budget_id,))
            result = c.fetchone()
            if result is None:
                print("Invalid ID. Budget does not exist.\n")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Show budget details before deleting
    c.execute("""
        SELECT b.id, c.name, b.amount, b.month, b.year
        FROM budgets b
        INNER JOIN categories c ON b.category_id = c.id
        WHERE b.id = ?
    """, (budget_id,))
    budget = c.fetchone()
    if budget:
        print("\n==== Budget To Delete ====\n")
        print(f"{'ID':<5} {'Category':<15} {'Amount':<10} {'month':<2} {'year':<4}")
        print("-" * 90)
        print(f"{budget[0]:<5} {budget[1]:<15} {budget[2]:<10.2f} {budget[3]:<2} {budget[4]:<4}")

    confirm = input("Are you sure you want to delete this budget? (y/n): ").lower()
    if confirm == "y":
        c.execute("DELETE FROM budgets WHERE id = ?", (budget_id,))
        conn.commit()
        print("\nBudget deleted.")
    else:
        print("\nDeletion cancelled.")

    conn.close()


def update_budget():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    while True:
        try:
            unique_id = int(input("Enter the ID of the budget you want to update: "))
            c.execute("SELECT id FROM budgets WHERE id = ?", (unique_id,))
            result = c.fetchone()
            if result is None:
                print("Invalid ID. Budget does not exist.\n")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    while True:
        try:
            result = int(input("Which field do you want to edit?:\n"
                               "1: Category ID\n"
                               "2: Amount\n"
                               "3: Date\n"))
            if result == 1:
                c.execute("SELECT category_id FROM budgets WHERE id = ?", (unique_id,))
                print("\nOld category id:", c.fetchone()[0])
                while True:
                    try:
                        category = int(input("Please enter your category ID: "))
                        if category > 0:
                            if category_exists(category):
                                break
                            else:
                                print("Category does not exist.")
                        else:
                            print("Category ID must be a positive integer.")
                    except ValueError:
                        print("Please enter a valid category ID.")
                c.execute("UPDATE budgets SET category_id = ? WHERE id = ?", (category, unique_id))

            elif result == 2:
                c.execute("SELECT amount FROM budgets WHERE id = ?", (unique_id,))
                old_amount = c.fetchone()[0]
                print("\nOld amount:", old_amount)
                while True:
                    try:
                        new_amount = float(input("Enter the new amount: "))
                        if new_amount <= 0:
                            print("New amount must be greater than 0.")
                            continue
                        break
                    except ValueError:
                        print("Invalid amount. Please enter a number.")
                c.execute("UPDATE budgets SET amount = ? WHERE id = ?", (new_amount, unique_id))

            elif result == 3:
                c.execute("SELECT month, year FROM budgets WHERE id = ?", (unique_id,))
                old_month, old_year = c.fetchone()
                print(f"\nOld period: Month {old_month}, Year {old_year}")
                while True:
                    try:
                        month = int(input("Please enter the month (1-12): "))
                        if 1 <= month <= 12:
                            break
                        else:
                            print("Month must be between 1 and 12.")
                    except ValueError:
                        print("Invalid input. Please enter a valid month.")
                while True:
                    try:
                        year = int(input("Please enter the year (YYYY): "))
                        if 1990 <= year <= 2100:
                            break
                        else:
                            print("Year must be a valid four-digit year.")
                    except ValueError:
                        print("Invalid input. Please enter a valid year.")
                c.execute("UPDATE budgets SET month = ?, year = ? WHERE id = ?", (month, year, unique_id))

            else:
                print("Please enter a number between 1 and 3.")
                continue

            print("\nBudget updated.")
            conn.commit()
            conn.close()
            break
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 3.")


def search_budget():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    # Ask for ID and validate
    while True:
        try:
            budget_id = int(input("What is the ID of the budget you want to search: "))
            # Check if budget exists
            c.execute("SELECT id FROM budgets WHERE id = ?", (budget_id,))
            result = c.fetchone()
            if result is None:
                print("Invalid ID. Budget does not exist.\n")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Fetch budget details with category name
    c.execute("""
        SELECT b.id, b.amount, c.name, b.month, b.year, b.created_at
        FROM budgets b
        INNER JOIN categories c ON b.category_id = c.id
        WHERE b.id = ?
    """, (budget_id,))

    budget = c.fetchone()
    if budget:
        print("\n==== Budget Details ====\n")
        # Print headers
        print(f"{'ID':<5} {'Amount':>12} {'Category':<15} {'Month':<8} {'Year':<6} {'Created At':<12}")
        print("-" * 70)
        # Print row
        bid = budget[0]
        amount = f"${budget[1]:,.2f}"
        category = budget[2]
        month = budget[3]
        year = budget[4]
        created_at = budget[5][:10]  # slice to YYYY-MM-DD
        print(f"{bid:<5} {amount:>12} {category:<15} {month:<8} {year:<6} {created_at:<12}")

    conn.close()


def financial_actions():
    conn = sqlite3.connect("database/finance.db")
    c = conn.cursor()
    while True:
        c.execute("SELECT COUNT(*) FROM budgets")
        count = c.fetchone()[0]
        if count == 0:
            print("There are no budgets.")
            break
        try:
            choice = int(input("Would you like to:\n"
                               "1: Update budget\n"
                               "2: Search budget\n"
                               "3: Delete budget\n"))
            if choice == 1:
                update_budget()
            elif choice == 2:
                search_budget()
            elif choice == 3:
                delete_budget()
            else:
                print("Invalid input. Please enter 1, 2, or 3.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter 1, 2, or 3.")
    conn.close()


def menu():
    while True:
        print("\n==== Budgets Menu ====")
        print("1: Add Budget")
        print("2: View/Filter Budgets")
        print("3: Search Budget by ID")
        print("4: Financial Actions (update/delete)")
        print("5: Budget Dashboard")
        print("6: Quick Summary")
        print("0: Back to Dashboard")

        try:
            choice = int(input("Select an option: "))
            if choice == 1:
                add_budget()
            elif choice == 2:
                while True:
                    print("\n==== View/Filter Budgets ====")
                    print("1: View all budgets")
                    print("2: Search by keyword")
                    print("3: Filter by category")
                    print("4: Filter by month/year")
                    print("5: Filter by date range (manual)")
                    print("6: Quick date range selector")  # new option
                    print("7: Sort by created date")
                    print("8: Sort by amount")
                    print("0: Back")

                    sub_choice = input("Select an option: ").strip()

                    if sub_choice == "1":
                        filter_budgets("all")
                    elif sub_choice == "2":
                        filter_budgets("keyword")
                    elif sub_choice == "3":
                        filter_budgets("category")
                    elif sub_choice == "4":
                        filter_budgets("month_year")
                    elif sub_choice == "5":
                        filter_budgets("date")
                    elif sub_choice == "6":
                        filter_budgets("range")  # new mode
                    elif sub_choice == "7":
                        filter_budgets("sort_date")
                    elif sub_choice == "8":
                        filter_budgets("sort_amount")
                    elif sub_choice == "0":
                        break
                    else:
                        print("Invalid choice. Please enter 0–8.")

            elif choice == 3:
                search_budget()
            elif choice == 4:
                financial_actions()
            elif choice == 5:
                budget_dashboard()
            elif choice == 6:
                budget_summary()
            elif choice == 0:
                break
            else:
                print("Invalid choice. Please enter 0–4.")
        except ValueError:
            print("Invalid input. Please enter a number.")