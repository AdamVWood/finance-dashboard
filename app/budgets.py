import sqlite3
from category import category_exists

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

    c.execute('''
        INSERT INTO budgets (category_id, amount, month, year)
        VALUES (?, ?, ?, ?)
        ''', (category, amount, month, year))  # enters the data
    conn.commit()
    conn.close()


def view_budgets():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT b.id, c.name, b.amount, b.month, b.year
        FROM budgets b
        INNER JOIN categories c ON b.category_id = c.id
    """)
    rows = c.fetchall()

    if not rows:
        print("No budgets found.")
    else:
        print("\n==== Budget History ====\n")
        # Print headers
        print(f"{'ID':<5} {'Category':<15} {'Amount':<10} {'month':<2} {'year':<4}")
        print("-" * 90)
        # Print each budget row
        for b in rows:
            print(f"{b[0]:<5} {b[1]:<15} {b[2]:<10.2f} {b[3]:<2} {b[4]:<4}")

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
            SELECT b.id, c.name, b.amount, b.month, b.year
            FROM budgets b
            INNER JOIN categories c ON b.category_id = c.id
            WHERE b.id = ?
            """, (budget_id,))

    budget = c.fetchone()
    if budget:
        print("\n==== Budget Details ====\n")
        print(f"{'ID':<5} {'Category':<15} {'Amount':<10} {'month':<2} {'year':<4}")
        print("-" * 90)
        print(f"{budget[0]:<5} {budget[1]:<15} {budget[2]:<10.2f} {budget[3]:<2} {budget[4]:<4}")
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
