import sqlite3
import datetime

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
            category = int(input("Please enter your category: "))
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
    c.execute("""SELECT t.amount, t.transaction_type, category_id, t.description, t.date, t.created_at
                  FROM transaction t
                  INNER JOIN categories c ON t.category_id = c.id""")
    c.execute("SELECT * FROM finance")
    rows = c.fetchall()

    if not rows:
        print("No transactions found.")

    else:
        print("\n==== Transactions History ====\n")
        for t in rows:
            # prints each row directly as a tuple
            print(t)

    conn.close()


# continue from here
def inventory_actions():
    conn = sqlite3.connect("inventory.db")
    c = conn.cursor()
    while True:
        try:
            choice = int(input("Would you like to:\n"
                               "1: Update transaction\n"
                               "2: Remove transaction\n"
                               "3: Search transaction\n"))
            if choice < 1 or choice > 3:
                print("Please enter a number between 1 and 3")
                continue
            elif choice == 1:
                while True:
                    try:
                        unique_id = int(input("Enter the ID of the transaction you want to update: "))

                        c.execute("SELECT ID FROM transactions WHERE id = ?", (unique_id,))
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
                                    category = int(input("Please enter your category: "))
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
                        break
                    except ValueError:
                        print("Invalid input. Please enter a number between 1 and 5.")

            elif choice == 2:
                c.execute("SELECT COUNT(*) FROM transactions")
                count = c.fetchone()[0]
                if count == 0:
                    print("There are no transactions.")
                    return
                while True:
                    try:
                        unique_id = int(input("Enter the ID of the transaction you want to delete: "))
                        c.execute("SELECT unique_ID FROM finance WHERE unique_ID = ?", (unique_id,))
                        result = c.fetchone()
                        if result is None:
                            print("Invalid ID. Transaction does not exist.\n")
                            continue
                        break

                    except ValueError:
                        print("Invalid input. Please enter a valid number.")

                c.execute("DELETE FROM finance WHERE unique_ID = ?", (unique_id,))
                print("\nTransaction deleted.")
            elif choice == 3:
                while True:
                    product_name = input("What is the name of the product you want to search: ")
                    if product_name:
                        break
                    else:
                        print("Please enter a valid product name.")
                c.execute("""SELECT p.name, c.name, p.price, p.quantity
                             FROM products p
                             INNER JOIN categories c ON p.category_id = c.id
                             WHERE p.name = ?""", (product_name,))
                products = c.fetchall()
                for product_name, category_name, price, quantity in products:
                    print(product_name)
                    print("Category:", category_name)
                    print("Price:", price)
                    print("Quantity:", quantity)
                    print("-" * 20)
            else:
                print("Invalid input. Please enter a number between 1 and 3.")
                continue
            conn.commit()
            conn.close()
            break
        except ValueError:
            print("Please enter a number between 1 and 3")

    conn.close() # single close at the very end