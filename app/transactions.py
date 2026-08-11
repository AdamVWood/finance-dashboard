import sqlite3
import datetime

def add_transaction():
    conn = sqlite3.connect('finance.db')
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

    c.execute('''INSERT INTO finance (amount, transaction_type, category_id, description, date, created_at)
                                     VALUES (?, ?, ?, ?, ?, ?)''',
              (amount, transaction_type, category, description, date, created_at))  # enters the data
    conn.commit()
    conn.close()


def view_transactions():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()

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


def update_transactions():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    print("\n==== Update Transaction ====\n")

    # Ask for ID and validate
    while True:
        try:
            unique_id = int(input("Enter the ID of the transaction you want to update: "))

            c.execute("SELECT unique_ID FROM finance WHERE unique_ID = ?", (unique_id,))
            result = c.fetchone()

            if result is None:
                print("Invalid ID. Transaction does not exist.\n")
                continue

            break

        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Get old amount
    c.execute("SELECT Amount FROM finance WHERE unique_ID = ?", (unique_id,))
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
        "UPDATE finance SET Amount = ? WHERE unique_ID = ?",
        (new_amount, unique_id)
    )
    print("\nTransaction updated.")
    conn.commit()
    conn.close()


def delete_transactions():
    conn = sqlite3.connect('finance.db')
    c = conn.cursor()
    c.execute("SELECT COUNT(*) FROM finance")
    # Ask for ID and validate
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
    conn.commit()
    conn.close()