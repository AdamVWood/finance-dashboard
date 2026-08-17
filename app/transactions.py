import sqlite3
import datetime
from app.categories import category_exists

def add_transaction():
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

    # Transaction type: must be one of 1–6
    while True:
        try:
            transaction_type = int(input(
                "Please enter your transaction type "
                "\n\tWithdrawal: 1 "
                "\n\tDeposit: 2"
                "\n\tTransfer: 3"
                "\n\tRemittance: 4"
                "\n\tDirect Debit: 5"
                "\n\tFee: 6\n"
                ":"
            ))
            if transaction_type not in range(1, 7):
                print("Invalid choice. Please enter a number between 1 and 6.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 6.")

    # Convert number to text before saving
    transaction_types = {
        1: "Withdrawal",
        2: "Deposit",
        3: "Transfer",
        4: "Remittance",
        5: "Direct Debit",
        6: "Fee"
    }
    transaction_type = transaction_types[transaction_type]

    # Category: cannot be empty
    while True:
        try:
            category = int(input("Please enter the category ID: "))
            if category > 0:
                if category_exists(category):
                    break
                else:
                    print("Category does not exist.")
            else:
                print("Category ID must be a positive integer.")
        except ValueError:
            print("Please enter a valid category ID.")

    # Description: cannot be empty
    while True:
        description = input("Please enter your description: ").strip()
        if description == "":
            print("Description cannot be empty.")
        else:
            break

    # Date: must match YYYY-MM-DD format
    while True:
        date = input("Please enter your date (YYYY-MM-DD): ").strip()
        try:
            datetime.datetime.strptime(date, "%Y-%m-%d")
            break
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

    created_at = datetime.datetime.today().strftime("%Y-%m-%d")

    c.execute('''INSERT INTO transactions (amount, transaction_type, category_id, description, date, created_at)
                                     VALUES (?, ?, ?, ?, ?, ?)''',
              (amount, transaction_type, category, description, date, created_at))  # enters the data
    conn.commit()
    conn.close()


def view_transactions():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT t.id, t.amount, t.transaction_type, c.name, t.description, t.date, t.created_at
        FROM transactions t
        INNER JOIN categories c ON t.category_id = c.id
    """)
    rows = c.fetchall()

    if not rows:
        print("No transactions found.")
    else:
        print("\n==== Transactions History ====\n")
        # Print headers
        print(
            f"{'ID':<5} {'Date':<12} {'Description':<20} {'Category':<15} {'Type':<10} {'Amount':>12} {'Created At':<12}")
        print("-" * 90)
        # Print each transaction row
        for row in rows:
            tid = row[0]
            date = row[1]
            description = row[2] if row[2] else ""
            category = row[3]
            t_type = row[4]
            amount = f"${row[5]:,.2f}"
            created_at = row[6][:10]  # slice to YYYY-MM-DD only
            print(f"{tid:<5} {date:<12} {description:<20} {category:<15} {t_type:<10} {amount:>12} {created_at:<12}")

    conn.close()


def delete_transaction():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    # Check if there are any transactions
    c.execute("SELECT COUNT(*) FROM transactions")
    if c.fetchone()[0] == 0:
        print("There are no transactions.")
        conn.close()
        return

    # Ask for ID and validate
    while True:
        try:
            transaction_id = int(input("Enter the ID of the transaction you want to delete: "))
            c.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
            result = c.fetchone()
            if result is None:
                print("Invalid ID. Transaction does not exist.\n")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Show transaction details before deleting
    c.execute("""
        SELECT t.id, t.amount, t.transaction_type, c.name, t.description, t.date, t.created_at
        FROM transactions t
        INNER JOIN categories c ON t.category_id = c.id
        WHERE t.id = ?
    """, (transaction_id,))
    transaction = c.fetchone()
    if transaction:
        print("\n==== Transaction To Delete ====\n")
        print(f"{'ID':<5} {'Amount':<10} {'Type':<15} {'Category':<15} {'Description':<40} {'Date':<12} {'Created At':<12}")
        print("-" * 90)
        print(f"{transaction[0]:<5} {transaction[1]:<10.2f} {transaction[2]:<15} {transaction[3]:<15} {transaction[4]:<20} {transaction[5]:<12} {transaction[6]:<12}")

    confirm = input("Are you sure you want to delete this transaction? (y/n): ").lower()
    if confirm == "y":
        c.execute("DELETE FROM transactions WHERE id = ?", (transaction_id,))
        conn.commit()
        print("\nTransaction deleted.")
    else:
        print("\nDeletion cancelled.")

    conn.close()


def update_transaction():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    while True:
        try:
            unique_id = int(input("Enter the ID of the transaction you want to update: "))

            c.execute("SELECT id FROM transactions WHERE id = ?", (unique_id,))
            result = c.fetchone()

            if result is None:
                print("Invalid ID. Transaction does not exist.\n")
                continue

            break

        except ValueError:
            print("Invalid input. Please enter a valid number.")
    while True:
        try:
            result = int(input("Which field do you want to edit?:\n"
                               "1: Amount\n"
                               "2: Transaction Type\n"
                               "3: Category ID\n"
                               "4: Description\n"
                               "5: Date\n"))
            if result == 1:
                # Get old amount
                c.execute("SELECT amount FROM transactions WHERE id = ?", (unique_id,))
                old_amount = c.fetchone()[0]
                print("\nOld amount:", old_amount)
                # Get new amount
                while True:
                    try:
                        new_amount = float(input("Enter the new amount: "))
                        if new_amount <= 0:
                            print("New amount must be greater than 0.")
                            continue
                        break
                    except ValueError:
                        print("Invalid amount. Please enter a number.")
                # Update database
                c.execute(
                    "UPDATE transactions SET amount = ? WHERE id = ?",
                    (new_amount, unique_id)
                )
            elif result == 2:
                # Transaction Type
                c.execute("SELECT transaction_type FROM transactions WHERE id = ?", (unique_id,))
                print("\nOld transaction type:", c.fetchone()[0])
                while True:
                    try:
                        transaction_type = int(input(
                            "Please enter your transaction type "
                            "\n\tWithdrawal: 1 "
                            "\n\tDeposit: 2"
                            "\n\tTransfer: 3"
                            "\n\tRemittance: 4"
                            "\n\tDirect Debit: 5"
                            "\n\tFee: 6\n"
                            ":"
                        ))
                        if transaction_type not in range(1, 7):
                            print("Invalid choice. Please enter a number between 1 and 6.")
                            continue
                        break
                    except ValueError:
                        print("Invalid input. Please enter a number between 1 and 6.")

                # Convert number to text before saving
                transaction_types = {
                    1: "Withdrawal",
                    2: "Deposit",
                    3: "Transfer",
                    4: "Remittance",
                    5: "Direct Debit",
                    6: "Fee"
                }
                transaction_type = transaction_types[transaction_type]
                c.execute("UPDATE transactions SET transaction_type = ? WHERE id = ?",
                          (transaction_type, unique_id))
            elif result == 3:
                c.execute("SELECT category_id FROM transactions WHERE id = ?", (unique_id,))
                print("\nOld category id:", c.fetchone()[0])
                while True:
                    try:
                        category = int(input("Please enter the category ID: "))
                        if category > 0:
                            if category_exists(category):
                                break
                            else:
                                print("Category does not exist.")
                        else:
                            print("Category ID must be a positive integer.")
                    except ValueError:
                        print("Please enter a valid category ID.")
                c.execute("UPDATE transactions SET category_id  = ? WHERE id = ?",
                          (category, unique_id))
            elif result == 4:
                c.execute("SELECT description FROM transactions WHERE id = ?", (unique_id,))
                print("\nOld description:", c.fetchone()[0])
                while True:
                    description = input("Please enter your description: ").strip()
                    if description == "":
                        print("Description cannot be empty.")
                    else:
                        break
                c.execute("UPDATE transactions SET description = ? WHERE id = ?",
                          (description, unique_id))
            elif result == 5:
                c.execute("SELECT date FROM transactions WHERE id = ?", (unique_id,))
                print("\nOld date:", c.fetchone()[0])
                while True:
                    date = input("Please enter your date (YYYY-MM-DD): ").strip()
                    try:
                        datetime.datetime.strptime(date, "%Y-%m-%d")
                        break
                    except ValueError:
                        print("Invalid date format. Please use YYYY-MM-DD.")
                c.execute("UPDATE transactions SET date = ? WHERE id = ?", (date, unique_id))
            else:
                print("Please enter a number between 1 and 5.")
                continue
            print("\nTransaction updated.")
            conn.commit()
            conn.close()
            break
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 5.")


def search_transaction():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    # Ask for ID and validate
    while True:
        try:
            transaction_id = int(input("What is the ID of the transaction you want to search: "))
            # Check if transaction exists
            c.execute("SELECT id FROM transactions WHERE id = ?", (transaction_id,))
            result = c.fetchone()
            if result is None:
                print("Invalid ID. Transaction does not exist.\n")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Fetch transaction details with category name
    c.execute("""
        SELECT t.id, t.date, t.description, c.name, t.transaction_type, t.amount, t.created_at
        FROM transactions t
        INNER JOIN categories c ON t.category_id = c.id
        WHERE t.id = ?
    """, (transaction_id,))

    transaction = c.fetchone()
    if transaction:
        print("\n==== Transaction Details ====\n")
        # Print headers
        print(f"{'ID':<5} {'Date':<12} {'Description':<20} {'Category':<15} {'Type':<10} {'Amount':>12} {'Created At':<12}")
        print("-" * 90)
        # Print row
        tid = transaction[0]
        date = transaction[1]
        description = transaction[2] if transaction[2] else ""
        category = transaction[3]
        t_type = transaction[4]
        amount = f"${transaction[5]:,.2f}"
        created_at = transaction[6][:10]  # slice to YYYY-MM-DD
        print(f"{tid:<5} {date:<12} {description:<20} {category:<15} {t_type:<10} {amount:>12} {created_at:<12}")

    conn.close()


def financial_actions():
    conn = sqlite3.connect("database/finance.db")
    c = conn.cursor()
    while True:
        c.execute("SELECT COUNT(*) FROM transactions")
        count = c.fetchone()[0]
        if count == 0:
            print("There are no transactions.")
            break
        try:
            choice = int(input("Would you like to:\n"
                               "1: Update transaction\n"
                               "2: Search transaction\n"
                               "3: Delete transaction\n"))
            if choice == 1:
                update_transaction()
            elif choice == 2:
                search_transaction()
            elif choice == 3:
                delete_transaction()
            else:
                print("Invalid input. Please enter 1, 2, or 3.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter 1, 2, or 3.")
    conn.close()


def menu():
    while True:
        print("\n==== Transactions Menu ====")
        print("1: Add Transaction")
        print("2: View Transactions")
        print("3: Financial Actions (update/search/delete)")
        print("0: Back to Dashboard")

        try:
            choice = int(input("Select an option: "))
            if choice == 1:
                add_transaction()
            elif choice == 2:
                view_transactions()
            elif choice == 3:
                financial_actions()
            elif choice == 0:
                break
            else:
                print("Invalid choice. Please enter 0–3.")
        except ValueError:
            print("Invalid input. Please enter a number.")
