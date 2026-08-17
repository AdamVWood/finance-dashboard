import sqlite3
import datetime
from app.categories import category_exists

def add_savings_goal():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    # Name: cannot be empty
    while True:
        name = input("Enter the savings goal name: ").strip()
        if name == "":
            print("Name cannot be empty.")
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

    # Target amount: must be positive
    while True:
        try:
            target_amount = float(input("Enter the target amount: "))
            if target_amount <= 0:
                print("Target amount must be greater than 0.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Current amount: must be >= 0
    while True:
        try:
            current_amount = float(input("Enter the current amount saved: "))
            if current_amount < 0:
                print("Current amount cannot be negative.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    # Deadline: must match YYYY-MM-DD
    while True:
        deadline = input("Enter the deadline (YYYY-MM-DD): ").strip()
        try:
            datetime.datetime.strptime(deadline, "%Y-%m-%d")
            break
        except ValueError:
            print("Invalid date format. Please use YYYY-MM-DD.")

    created_at = datetime.datetime.today().strftime("%Y-%m-%d")

    c.execute('''
        INSERT INTO savings_goals (name, category_id, target_amount, current_amount, deadline, created_at)
        VALUES (?, ?, ?, ?, ?, ?)
    ''', (name, category_id, target_amount, current_amount, deadline, created_at))

    conn.commit()
    conn.close()
    print("\nSavings goal added successfully.")


def view_savings_goals():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT g.id, g.name, c.name, g.target_amount, g.current_amount, g.deadline, g.created_at
        FROM savings_goals g
        INNER JOIN categories c ON g.category_id = c.id
    """)
    rows = c.fetchall()

    if not rows:
        print("No savings goals found.")
    else:
        print("\n==== Savings Goals ====\n")
        print(f"{'ID':<5} {'Name':<20} {'Category':<15} {'Target':<10} {'Current':<10} {'Deadline':<12} {'Created At':<12}")
        print("-" * 100)
        for g in rows:
            print(f"{g[0]:<5} {g[1]:<20} {g[2]:<15} {g[3]:<10.2f} {g[4]:<10.2f} {g[5]:<12} {g[6]:<12}")

    conn.close()


def delete_savings_goal():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    c.execute("SELECT COUNT(*) FROM savings_goals")
    if c.fetchone()[0] == 0:
        print("There are no savings goals.")
        conn.close()
        return

    while True:
        try:
            goal_id = int(input("Enter the ID of the savings goal to delete: "))
            c.execute("SELECT id FROM savings_goals WHERE id = ?", (goal_id,))
            if c.fetchone() is None:
                print("Invalid ID. Savings goal does not exist.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    c.execute("""
        SELECT g.id, g.name, c.name, g.target_amount, g.current_amount, g.deadline, g.created_at
        FROM savings_goals g
        INNER JOIN categories c ON g.category_id = c.id
        WHERE g.id = ?
    """, (goal_id,))
    goal = c.fetchone()
    if goal:
        print("\n==== Savings Goal To Delete ====\n")
        print(f"{'ID':<5} {'Name':<20} {'Category':<15} {'Target':<10} {'Current':<10} {'Deadline':<12} {'Created At':<12}")
        print("-" * 100)
        print(f"{goal[0]:<5} {goal[1]:<20} {goal[2]:<15} {goal[3]:<10.2f} {goal[4]:<10.2f} {goal[5]:<12} {goal[6]:<12}")

    confirm = input("Are you sure you want to delete this savings goal? (y/n): ").lower()
    if confirm == "y":
        c.execute("DELETE FROM savings_goals WHERE id = ?", (goal_id,))
        conn.commit()
        print("\nSavings goal deleted.")
    else:
        print("\nDeletion cancelled.")

    conn.close()


def update_savings_goal():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    while True:
        try:
            goal_id = int(input("Enter the ID of the savings goal to update: "))
            c.execute("SELECT id FROM savings_goals WHERE id = ?", (goal_id,))
            if c.fetchone() is None:
                print("Invalid ID. Savings goal does not exist.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    while True:
        try:
            choice = int(input("Which field do you want to edit?\n1: Name\n2: Target Amount\n3: Current Amount\n4: Deadline\n5: Category ID\n"))
            if choice == 1:
                old_name = c.execute("SELECT name FROM savings_goals WHERE id = ?", (goal_id,)).fetchone()[0]
                print("\nOld name:", old_name)
                new_name = input("Enter new name: ").strip()
                c.execute("UPDATE savings_goals SET name = ? WHERE id = ?", (new_name, goal_id))
            elif choice == 2:
                old_target = c.execute("SELECT target_amount FROM savings_goals WHERE id = ?", (goal_id,)).fetchone()[0]
                print("\nOld target amount:", old_target)
                while True:
                    try:
                        new_target = float(input("Enter new target amount: "))
                        if new_target <= 0:
                            print("Target must be greater than 0.")
                            continue
                        break
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                c.execute("UPDATE savings_goals SET target_amount = ? WHERE id = ?", (new_target, goal_id))
            elif choice == 3:
                old_current = c.execute("SELECT current_amount FROM savings_goals WHERE id = ?", (goal_id,)).fetchone()[0]
                print("\nOld current amount:", old_current)
                while True:
                    try:
                        new_current = float(input("Enter new current amount: "))
                        if new_current < 0:
                            print("Current amount cannot be negative.")
                            continue
                        break
                    except ValueError:
                        print("Invalid input. Please enter a number.")
                c.execute("UPDATE savings_goals SET current_amount = ? WHERE id = ?", (new_current, goal_id))
            elif choice == 4:
                old_deadline = c.execute("SELECT deadline FROM savings_goals WHERE id = ?", (goal_id,)).fetchone()[0]
                print("\nOld deadline:", old_deadline)
                while True:
                    new_deadline = input("Enter new deadline (YYYY-MM-DD): ").strip()
                    try:
                        datetime.datetime.strptime(new_deadline, "%Y-%m-%d")
                        break
                    except ValueError:
                        print("Invalid date format. Please use YYYY-MM-DD.")
                c.execute("UPDATE savings_goals SET deadline = ? WHERE id = ?", (new_deadline, goal_id))
            elif choice == 5:
                old_cat = c.execute("SELECT category_id FROM savings_goals WHERE id = ?", (goal_id,)).fetchone()[0]
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
                c.execute("UPDATE savings_goals SET category_id = ? WHERE id = ?", (category_id, goal_id))
            else:
                print("Please enter a number between 1 and 5.")
                continue

            conn.commit()
            print("\nSavings goal updated.")
            break
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 5.")

    conn.close()


def search_savings_goal():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    while True:
        try:
            goal_id = int(input("Enter the ID of the savings goal to search: "))
            c.execute("SELECT id FROM savings_goals WHERE id = ?", (goal_id,))
            if c.fetchone() is None:
                print("Invalid ID. Savings goal does not exist.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a number.")

    c.execute("""
        SELECT g.id, g.name, c.name, g.target_amount, g.current_amount, g.deadline, g.created_at
        FROM savings_goals g
        INNER JOIN categories c ON g.category_id = c.id
        WHERE g.id = ?
    """, (goal_id,))
    goal = c.fetchone()
    if goal:
        print("\n==== Savings Goal Details ====\n")
        print(f"{'ID':<5} {'Name':<20} {'Category':<15} {'Target':<10} {'Current':<10} {'Deadline':<12} {'Created At':<12}")
        print("-" * 100)
        print(f"{goal[0]:<5} {goal[1]:<20} {goal[2]:<15} {goal[3]:<10.2f} {goal[4]:<10.2f} {goal[5]:<12} {goal[6]:<12}")

    conn.close()


def financial_actions():
    conn = sqlite3.connect("database/finance.db")
    c = conn.cursor()
    while True:
        c.execute("SELECT COUNT(*) FROM savings_goals")
        count = c.fetchone()[0]
        if count == 0:
            print("There are no savings goals.")
            break
        try:
            choice = int(input("Would you like to:\n"
                               "1: Update savings goal\n"
                               "2: Search savings goal\n"
                               "3: Delete savings goal\n"))
            if choice == 1:
                update_savings_goal()
            elif choice == 2:
                search_savings_goal()
            elif choice == 3:
                delete_savings_goal()
            else:
                print("Invalid input. Please enter 1, 2, or 3.")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter 1, 2, or 3.")
    conn.close()


def menu():
    while True:
        print("\n==== Saving Goal Menu ====")
        print("1: Add Saving Goal")
        print("2: View Saving Goals")
        print("3: Financial Actions (update/search/delete)")
        print("0: Back to Dashboard")

        try:
            choice = int(input("Select an option: "))
            if choice == 1:
                add_savings_goal()
            elif choice == 2:
                view_savings_goals()
            elif choice == 3:
                financial_actions()
            elif choice == 0:
                break
            else:
                print("Invalid choice. Please enter 0–3.")
        except ValueError:
            print("Invalid input. Please enter a number.")
