import sqlite3
import datetime
from app.categories import category_exists

def add_investment():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    # Name: cannot be empty
    while True:
        name = input("Enter the investment name: ").strip()
        if name == "":
            print("Name cannot be empty.")
        else:
            break

    # Ticker: cannot be empty
    while True:
        ticker = input("Enter the ticker symbol: ").strip().upper()
        if ticker == "":
            print("Ticker cannot be empty.")
        else:
            break

    # Asset type: cannot be empty
    while True:
        asset_type = input("Enter the asset type (e.g., Stock, Bond, ETF): ").strip()
        if asset_type == "":
            print("Asset type cannot be empty.")
        else:
            break

    # Category: must exist
    while True:
        try:
            category_id = int(input("Enter the category ID: "))
            if category_id > 0:
                if category_exists(category_id):
                    break
                else:
                    print("Category does not exist.")
            else:
                print("Category ID must be a positive integer.")
        except ValueError:
            print("Please enter a valid category ID.")

    # Quantity: must be positive
    while True:
        try:
            quantity = float(input("Enter the quantity: "))
            if quantity <= 0:
                print("Quantity must be greater than 0.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Purchase price: must be positive
    while True:
        try:
            purchase_price = float(input("Enter the purchase price: "))
            if purchase_price <= 0:
                print("Purchase price must be greater than 0.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Purchase date: must match YYYY-MM-DD
    while True:
        purchase_date = input("Enter the purchase date (YYYY-MM-DD): ").strip()
        try:
            datetime.datetime.strptime(purchase_date, "%Y-%m-%d")
            break
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

    created_at = datetime.datetime.today().strftime("%Y-%m-%d")

    c.execute('''
        INSERT INTO investments (name, ticker, asset_type, category_id, quantity, purchase_price, purchase_date, created_at)
        VALUES (?, ?, ?, ?, ?, ?, ?, ?)
    ''', (name, ticker, asset_type, category_id, quantity, purchase_price, purchase_date, created_at))

    conn.commit()
    conn.close()
    print("\nInvestment added successfully.")


def view_investments():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT i.id, i.name, i.ticker, i.asset_type, c.name, i.quantity, i.purchase_price, i.purchase_date, i.created_at
        FROM investments i
        INNER JOIN categories c ON i.category_id = c.id
    """)
    rows = c.fetchall()

    if not rows:
        print("No investments found.")
    else:
        print("\n==== Investments ====\n")
        print(f"{'ID':<5} {'Name':<20} {'Ticker':<10} {'Type':<10} {'Category':<15} {'Quantity':<10} {'Price':<10} {'Date':<12} {'Created At':<12}")
        print("-" * 100)
        for inv in rows:
            print(f"{inv[0]:<5} {inv[1]:<20} {inv[2]:<10} {inv[3]:<10} {inv[4]:<15} {inv[5]:<10.2f} {inv[6]:<10.2f} {inv[7]:<12} {inv[8]:<12}")

    conn.close()


def delete_investment():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM investments")
    if c.fetchone()[0] == 0:
        print("There are no investments.")
        conn.close()
        return

    while True:
        try:
            inv_id = int(input("Enter the ID of the investment to delete: "))
            c.execute("SELECT id FROM investments WHERE id = ?", (inv_id,))
            if c.fetchone() is None:
                print("Invalid ID. Investment does not exist.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    c.execute("SELECT id, name, ticker, asset_type, quantity, purchase_price, purchase_date FROM investments WHERE id = ?", (inv_id,))
    inv = c.fetchone()
    if inv:
        print("\n==== Investment To Delete ====\n")
        print(f"{'ID':<5} {'Name':<20} {'Ticker':<10} {'Type':<10} {'Quantity':<10} {'Price':<10} {'Date':<12}")
        print("-" * 80)
        print(f"{inv[0]:<5} {inv[1]:<20} {inv[2]:<10} {inv[3]:<10} {inv[4]:<10.2f} {inv[5]:<10.2f} {inv[6]:<12}")

    confirm = input("Are you sure you want to delete this investment? (y/n): ").lower()
    if confirm == "y":
        c.execute("DELETE FROM investments WHERE id = ?", (inv_id,))
        conn.commit()
        print("\nInvestment deleted.")
    else:
        print("\nDeletion cancelled.")

    conn.close()


def update_investment():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    while True:
        try:
            inv_id = int(input("Enter the ID of the investment to update: "))
            c.execute("SELECT id FROM investments WHERE id = ?", (inv_id,))
            if c.fetchone() is None:
                print("Invalid ID. Investment does not exist.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    while True:
        try:
            choice = int(input("Which field do you want to edit?\n1: Name\n2: Ticker\n3: Asset Type\n4: Quantity\n5: Purchase Price\n6: Purchase Date\n"))
            if choice == 1:
                old_name = c.execute("SELECT name FROM investments WHERE id = ?", (inv_id,)).fetchone()[0]
                print("\nOld name:", old_name)
                new_name = input("Enter new name: ").strip()
                c.execute("UPDATE investments SET name = ? WHERE id = ?", (new_name, inv_id))
            elif choice == 2:
                old_ticker = c.execute("SELECT ticker FROM investments WHERE id = ?", (inv_id,)).fetchone()[0]
                print("\nOld ticker:", old_ticker)
                new_ticker = input("Enter new ticker: ").strip().upper()
                c.execute("UPDATE investments SET ticker = ? WHERE id = ?", (new_ticker, inv_id))
            elif choice == 3:
                old_type = c.execute("SELECT asset_type FROM investments WHERE id = ?", (inv_id,)).fetchone()[0]
                print("\nOld asset type:", old_type)
                new_type = input("Enter new asset type: ").strip()
                c.execute("UPDATE investments SET asset_type = ? WHERE id = ?", (new_type, inv_id))
            elif choice == 4:
                old_cat = c.execute("SELECT category_id FROM investments WHERE id = ?", (inv_id,)).fetchone()[0]
                print("\nOld category id:", old_cat)
                while True:
                    try:
                        category_id = int(input("Enter new category ID: "))
                        if category_id > 0:
                            if category_exists(category_id):
                                break
                            else:
                                print("Category does not exist.")
                        else:
                            print("Category ID must be a positive integer.")
                    except ValueError:
                        print("Please enter a valid category ID.")
                c.execute("UPDATE investments SET category_id = ? WHERE id = ?", (category_id, inv_id))
            elif choice == 5:
                old_price = c.execute("SELECT purchase_price FROM investments WHERE id = ?", (inv_id,)).fetchone()[0]
                print("\nOld purchase price:", old_price)
                while True:
                    try:
                        new_price = float(input("Enter new purchase price: "))
                        if new_price <= 0:
                            print("Price must be greater than 0.")
                            continue
                        break
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                c.execute("UPDATE investments SET purchase_price = ? WHERE id = ?", (new_price, inv_id))
            elif choice == 6:
                old_date = c.execute("SELECT purchase_date FROM investments WHERE id = ?", (inv_id,)).fetchone()[0]
                print("\nOld purchase date:", old_date)
                while True:
                    new_date = input("Enter new purchase date (YYYY-MM-DD): ").strip()
                    try:
                        datetime.datetime.strptime(new_date, "%Y-%m-%d")
                        break
                    except ValueError:
                        print("Invalid date format. Please use YYYY-MM-DD.")
                c.execute("UPDATE investments SET purchase_date = ? WHERE id = ?", (new_date, inv_id))
            else:
                print("Please enter a number between 1 and 6.")
                continue

            conn.commit()
            print("\nInvestment updated.")
            break
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 6.")

    conn.close()


def search_investment():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    while True:
        try:
            inv_id = int(input("Enter the ID of the investment to search: "))
            c.execute("SELECT id FROM investments WHERE id = ?", (inv_id,))
            if c.fetchone() is None:
                print("Invalid ID. Investment does not exist.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    c.execute("SELECT id, name, ticker, asset_type, quantity, purchase_price, purchase_date FROM investments WHERE id = ?", (inv_id,))
    inv = c.fetchone()
    if inv:
        print("\n==== Investment Details ====\n")
        print(f"{'ID':<5} {'Name':<20} {'Ticker':<10} {'Type':<10} {'Quantity':<10} {'Price':<10} {'Date':<12}")
        print("-" * 80)
        print(f"{inv[0]:<5} {inv[1]:<20} {inv[2]:<10} {inv[3]:<10} {inv[4]:<10.2f} {inv[5]:<10.2f} {inv[6]:<12}")

    conn.close()


def financial_actions():
    conn = sqlite3.connect("database/finance.db")
    c = conn.cursor()
    while True:
        c.execute("SELECT COUNT(*) FROM investments")
        count = c.fetchone()[0]
        if count == 0:
            print("There are no investments.")
            break
        try:
            choice = int(input("Would you like to:\n"
                               "1: Update investment\n"
                               "2: Search investment\n"
                               "3: Delete investment\n"))
            if choice == 1:
                update_investment()
            elif choice == 2:
                search_investment()
            elif choice == 3:
                delete_investment()
            else:
                print("Invalid input. Please enter 1, 2, or 3.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter 1, 2, or 3.")
    conn.close()


def menu():
    while True:
        print("\n==== Investments Menu ====")
        print("1: Add Investment")
        print("2: View Investments")
        print("3: Financial Actions (update/search/delete)")
        print("0: Back to Dashboard")

        try:
            choice = int(input("Select an option: "))
            if choice == 1:
                add_investment()
            elif choice == 2:
                view_investments()
            elif choice == 3:
                financial_actions()
            elif choice == 0:
                break
            else:
                print("Invalid choice. Please enter 0–3.")
        except ValueError:
            print("Invalid input. Please enter a number.")

