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


def filter_investments(mode="all"):
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    query = """
        SELECT id, name, ticker, asset_type, quantity, purchase_price, purchase_date, created_at
        FROM investments
    """
    params = []
    order_clause = ""

    if mode == "keyword":
        keyword = input("Enter keyword (name/ticker/type): ").strip()
        if not keyword:
            print("Error: Keyword cannot be empty.")
            conn.close()
            return
        query += " WHERE name LIKE ? OR ticker LIKE ? OR asset_type LIKE ?"
        params = [f"%{keyword}%", f"%{keyword}%", f"%{keyword}%"]

    elif mode == "type":
        asset_type = input("Enter asset type (Equity, Bond, Crypto, etc.): ").strip()
        if not asset_type:
            print("Error: Asset type cannot be empty.")
            conn.close()
            return
        # Optional: enforce known types
        valid_types = ["Equity", "Bond", "Crypto", "ETF", "Mutual Fund"]
        if asset_type not in valid_types:
            print(f"Error: '{asset_type}' is not a recognized type. Valid options: {', '.join(valid_types)}")
            conn.close()
            return
        query += " WHERE asset_type = ?"
        params = [asset_type]

    elif mode == "date":
        import datetime
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

        query += " WHERE purchase_date BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "sort_date":
        order_clause = " ORDER BY purchase_date DESC"

    elif mode == "sort_value":
        query = """
            SELECT id, name, ticker, asset_type, quantity, purchase_price, purchase_date, created_at,
                   (quantity * purchase_price) AS total_value
            FROM investments
            ORDER BY total_value DESC
        """

    elif mode == "all":
        order_clause = " ORDER BY purchase_date DESC"

    # Execute query
    c.execute(query + order_clause, params)
    rows = c.fetchall()

    if not rows:
        print("No matching investments found.")
    else:
        print("\n==== Investments ====\n")
        print(f"{'ID':<5} {'Name':<20} {'Ticker':<10} {'Type':<12} {'Qty':>8} {'Price':>12} {'Date':<12} {'Created At':<12}")
        print("-" * 95)
        for row in rows:
            iid = row[0]
            name = row[1]
            ticker = row[2]
            asset_type = row[3]
            qty = row[4]
            price = f"${row[5]:,.2f}"
            purchase_date = row[6]
            created_at = row[7][:10]
            print(f"{iid:<5} {name:<20} {ticker:<10} {asset_type:<12} {qty:>8} {price:>12} {purchase_date:<12} {created_at:<12}")

    conn.close()


def view_investments():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, ticker, asset_type, quantity, purchase_price, purchase_date, created_at
        FROM investments
        ORDER BY purchase_date DESC
    """)
    rows = c.fetchall()

    if not rows:
        print("No investments found.")
    else:
        print("\n==== Investments Overview ====\n")
        # Print headers
        print(f"{'ID':<5} {'Name':<20} {'Ticker':<10} {'Type':<12} {'Qty':>8} {'Price':>12} {'Date':<12} {'Created At':<12}")
        print("-" * 95)
        # Print each investment row
        for row in rows:
            iid = row[0]
            name = row[1]
            ticker = row[2]
            asset_type = row[3]
            qty = row[4]
            price = f"${row[5]:,.2f}"
            purchase_date = row[6]
            created_at = row[7][:10]  # slice to YYYY-MM-DD
            print(f"{iid:<5} {name:<20} {ticker:<10} {asset_type:<12} {qty:>8} {price:>12} {purchase_date:<12} {created_at:<12}")

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

    # Ask for ID and validate
    while True:
        try:
            investment_id = int(input("What is the ID of the investment you want to search: "))
            # Check if investment exists
            c.execute("SELECT id FROM investments WHERE id = ?", (investment_id,))
            result = c.fetchone()
            if result is None:
                print("Invalid ID. Investment does not exist.\n")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Fetch investment details
    c.execute("""
        SELECT id, name, ticker, asset_type, quantity, purchase_price, purchase_date, created_at
        FROM investments
        WHERE id = ?
    """, (investment_id,))

    investment = c.fetchone()
    if investment:
        print("\n==== Investment Details ====\n")
        # Print headers
        print(f"{'ID':<5} {'Name':<20} {'Ticker':<10} {'Type':<12} {'Qty':>8} {'Price':>12} {'Date':<12} {'Created At':<12}")
        print("-" * 95)
        # Print row
        iid = investment[0]
        name = investment[1]
        ticker = investment[2]
        asset_type = investment[3]
        qty = investment[4]
        price = f"${investment[5]:,.2f}"
        purchase_date = investment[6]
        created_at = investment[7][:10]  # slice to YYYY-MM-DD
        print(f"{iid:<5} {name:<20} {ticker:<10} {asset_type:<12} {qty:>8} {price:>12} {purchase_date:<12} {created_at:<12}")

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
        print("2: View/Filter Investments")
        print("3: Search Investment by ID")
        print("4: Financial Actions (update/delete)")
        print("0: Back to Dashboard")

        try:
            choice = int(input("Select an option: "))
            if choice == 1:
                add_investment()
            elif choice == 2:
                # Submenu for viewing/filtering
                while True:
                    print("\n==== View/Filter Investments ====")
                    print("1: View all investments")
                    print("2: Search by keyword (name/ticker/type)")
                    print("3: Filter by type")
                    print("4: Filter by purchase date range")
                    print("5: Sort by purchase date")
                    print("6: Sort by total value")
                    print("0: Back")

                    sub_choice = input("Select an option: ").strip()

                    if sub_choice == "1":
                        view_investments()
                    elif sub_choice == "2":
                        filter_investments("keyword")
                    elif sub_choice == "3":
                        filter_investments("type")
                    elif sub_choice == "4":
                        filter_investments("date")
                    elif sub_choice == "5":
                        filter_investments("sort_date")
                    elif sub_choice == "6":
                        filter_investments("sort_value")
                    elif sub_choice == "0":
                        break
                    else:
                        print("Invalid choice. Please enter 0–6.")

            elif choice == 3:
                search_investment()  # ID-based search
            elif choice == 4:
                financial_actions()  # update/delete
            elif choice == 0:
                break
            else:
                print("Invalid choice. Please enter 0–4.")
        except ValueError:
            print("Invalid input. Please enter a number.")
