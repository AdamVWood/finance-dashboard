import sqlite3


def category_exists(category_id):
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
    result = c.fetchone()
    conn.close()
    return result is not None


def add_category():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    while True:
        name = input("Enter category name: ").strip()
        if name == "":
            print("Category name cannot be empty.")
        else:
            break
    c.execute("INSERT INTO categories (name) VALUES (?)", (name,))
    conn.commit()
    conn.close()
    print("\nCategory added successfully.")


def view_categories():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, created_at
        FROM categories
        ORDER BY name ASC
    """)
    rows = c.fetchall()

    if not rows:
        print("No categories found.")
    else:
        print("\n==== Categories Overview ====\n")
        # Print headers
        print(f"{'ID':<5} {'Name':<20} {'Created At':<12}")
        print("-" * 40)
        # Print each category row
        for row in rows:
            cid = row[0]
            name = row[1]
            created_at = row[2][:10]  # slice to YYYY-MM-DD
            print(f"{cid:<5} {name:<20} {created_at:<12}")

    conn.close()


def delete_category():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM categories")
    if c.fetchone()[0] == 0:
        print("There are no categories.")
        conn.close()
        return

    while True:
        try:
            cat_id = int(input("Enter the ID of the category to delete: "))
            c.execute("SELECT id FROM categories WHERE id = ?", (cat_id,))
            if c.fetchone() is None:
                print("Invalid ID. Category does not exist.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    cat = c.execute("SELECT id, name FROM categories WHERE id = ?", (cat_id,)).fetchone()
    if cat:
        print("\n==== Category To Delete ====\n")
        print(f"{'ID':<5} {'Name':<20}")
        print("-" * 30)
        print(f"{cat[0]:<5} {cat[1]:<20}")

    confirm = input("Are you sure you want to delete this category? (y/n): ").lower()
    if confirm == "y":
        c.execute("DELETE FROM categories WHERE id = ?", (cat_id,))
        conn.commit()
        print("\nCategory deleted.")
    else:
        print("\nDeletion cancelled.")

    conn.close()


def update_category():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    while True:
        try:
            cat_id = int(input("Enter the ID of the category to update: "))
            c.execute("SELECT id FROM categories WHERE id = ?", (cat_id,))
            if c.fetchone() is None:
                print("Invalid ID. Category does not exist.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    old_name = c.execute("SELECT name FROM categories WHERE id = ?", (cat_id,)).fetchone()[0]
    print("\nOld name:", old_name)
    new_name = input("Enter new category name: ").strip()
    if new_name == "":
        print("Category name cannot be empty.")
    else:
        c.execute("UPDATE categories SET name = ? WHERE id = ?", (new_name, cat_id))
        conn.commit()
        print("\nCategory updated.")

    conn.close()


def search_category():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    # Ask for ID and validate
    while True:
        try:
            category_id = int(input("What is the ID of the category you want to search: "))
            # Check if category exists
            c.execute("SELECT id FROM categories WHERE id = ?", (category_id,))
            result = c.fetchone()
            if result is None:
                print("Invalid ID. Category does not exist.\n")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Fetch category details
    c.execute("""
        SELECT id, name, created_at
        FROM categories
        WHERE id = ?
    """, (category_id,))

    category = c.fetchone()
    if category:
        print("\n==== Category Details ====\n")
        # Print headers
        print(f"{'ID':<5} {'Name':<20} {'Created At':<12}")
        print("-" * 40)
        # Print row
        cid = category[0]
        name = category[1]
        created_at = category[2][:10]  # slice to YYYY-MM-DD
        print(f"{cid:<5} {name:<20} {created_at:<12}")

    conn.close()


def financial_actions():
    conn = sqlite3.connect("database/finance.db")
    c = conn.cursor()
    while True:
        c.execute("SELECT COUNT(*) FROM categories")
        count = c.fetchone()[0]
        if count == 0:
            print("There are no categories.")
            break
        try:
            choice = int(input("Would you like to:\n"
                               "1: Update category\n"
                               "2: Search category\n"
                               "3: Delete category\n"))
            if choice == 1:
                update_category()
            elif choice == 2:
                search_category()
            elif choice == 3:
                delete_category()
            else:
                print("Invalid input. Please enter 1, 2, or 3.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter 1, 2, or 3.")
    conn.close()


def menu():
    while True:
        print("\n==== Categories Menu ====")
        print("1: Add Category")
        print("2: View Categories")
        print("3: Financial Actions (update/search/delete)")
        print("0: Back to Dashboard")

        try:
            choice = int(input("Select an option: "))
            if choice == 1:
                add_category()
            elif choice == 2:
                view_categories()
            elif choice == 3:
                financial_actions()
            elif choice == 0:
                break
            else:
                print("Invalid choice. Please enter 0–3.")
        except ValueError:
            print("Invalid input. Please enter a number.")

