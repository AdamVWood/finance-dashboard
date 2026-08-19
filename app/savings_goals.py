import sqlite3
import datetime
from app.categories import category_exists


def add_money_to_goal():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    goal_id = int(input("Enter the ID of the savings goal to update: "))
    c.execute("SELECT target_amount, current_amount, deadline FROM savings_goals WHERE id = ?", (goal_id,))
    goal = c.fetchone()

    if not goal:
        print("Savings goal not found.")
        conn.close()
        return

    target, current, deadline = goal
    target = float(target or 0)
    current = float(current or 0)

    try:
        add_amount = float(input("Enter the amount to add: "))
        if add_amount <= 0:
            print("Amount must be greater than 0.")
            conn.close()
            return
    except ValueError:
        print("Invalid input.")
        conn.close()
        return

    new_current = current + add_amount
    c.execute("UPDATE savings_goals SET current_amount = ? WHERE id = ?", (new_current, goal_id))
    conn.commit()

    # Calculate progress
    remaining = target - new_current
    progress = (new_current / target * 100) if target > 0 else 0

    # Required monthly contribution
    deadline_date = datetime.datetime.strptime(deadline, "%Y-%m-%d")
    months_left = max(1, (deadline_date.year - datetime.date.today().year) * 12 +
                         (deadline_date.month - datetime.date.today().month))
    required_monthly = remaining / months_left if remaining > 0 else 0

    # On-track status
    state = "On track" if progress >= (100 * (datetime.date.today().month / 12)) else "Behind schedule"

    print("\n==== Updated Savings Goal ====")
    print(f"Current: ${new_current:.2f} / Target: ${target:.2f}")
    print(f"Remaining: ${remaining:.2f}")
    print(f"Progress: {progress:.0f}%")
    print(f"Required Monthly Contribution: ${required_monthly:.2f}")
    print(f"Status: {state}")

    conn.close()


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
        start = datetime.date(1970, 1, 1)  # effectively no limit
        end = today
    else:
        return None, None
    return start.strftime("%Y-%m-%d"), end.strftime("%Y-%m-%d")


def filter_savings_goals(mode="all"):
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    query = """
        SELECT id, name, target_amount, current_amount, deadline, created_at
        FROM savings_goals
    """
    params = []
    order_clause = ""

    if mode == "keyword":
        keyword = input("Enter keyword (name): ").strip()
        if not keyword:
            print("Error: Keyword cannot be empty.")
            conn.close()
            return
        query += " WHERE name LIKE ?"
        params = [f"%{keyword}%"]

    elif mode == "range":
        print("\nSelect a deadline range:")
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
        query += " WHERE deadline BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "date":
        start_date = input("Enter start deadline (YYYY-MM-DD): ").strip()
        end_date = input("Enter end deadline (YYYY-MM-DD): ").strip()
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
        query += " WHERE deadline BETWEEN ? AND ?"
        params = [start_date, end_date]

    elif mode == "sort_deadline":
        order_clause = " ORDER BY deadline ASC"

    elif mode == "sort_target":
        order_clause = " ORDER BY target_amount DESC"

    elif mode == "sort_current":
        order_clause = " ORDER BY current_amount DESC"

    elif mode == "all":
        order_clause = " ORDER BY deadline ASC"

    c.execute(query + order_clause, params)
    rows = c.fetchall()

    if not rows:
        print("No matching savings goals found.")
    else:
        print("\n==== Savings Goals ====\n")
        for row in rows:
            sid = row[0]
            name = row[1]
            target = float(row[2] or 0)
            current = float(row[3] or 0)
            deadline = row[4]
            created_at = row[5][:10]  # slice to YYYY-MM-DD

            progress = (current / target * 100) if target > 0 else 0
            remaining = target - current

            # Progress bar
            bar_length = 20
            filled = int(bar_length * progress / 100)
            bar = "█" * filled + "░" * (bar_length - filled)

            print(f"\n{name} (ID: {sid})")
            print(f"${current:.2f} / ${target:.2f}")
            print(f"{bar} {progress:.0f}%")
            print(f"Remaining: ${remaining:.2f}")
            print(f"Deadline: {deadline}")
            print(f"Created At: {created_at}")

    conn.close()


def view_savings_goals():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()
    c.execute("""
        SELECT id, name, target_amount, current_amount, deadline, created_at
        FROM savings_goals
        ORDER BY deadline ASC
    """)
    rows = c.fetchall()

    if not rows:
        print("No savings goals found.")
    else:
        print("\n==== Savings Goals Overview ====\n")
        for row in rows:
            sid = row[0]
            name = row[1]
            target = float(row[2] or 0)
            current = float(row[3] or 0)
            deadline = row[4]
            # Inline slice avoids “unused variable” warning
            created_at_str = row[5][:10]

            progress = (current / target * 100) if target > 0 else 0
            remaining = target - current

            # Progress bar
            bar_length = 20
            filled = int(bar_length * progress / 100)
            bar = "█" * filled + "░" * (bar_length - filled)

            print(f"\n{name} (ID: {sid})")
            print(f"${current:.2f} / ${target:.2f}")
            print(f"{bar} {progress:.0f}%")
            print(f"Remaining: ${remaining:.2f}")
            print(f"Deadline: {deadline}")
            print(f"Created At: {created_at_str}")

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
            choice = int(input("Which field do you want to edit?\n"
                               "1: Name\n2: Target Amount\n3: Current Amount\n4: Deadline\n5: Category ID\n"))
            if choice == 1:
                new_name = input("Enter new name: ").strip()
                c.execute("UPDATE savings_goals SET name = ? WHERE id = ?", (new_name, goal_id))
            elif choice == 2:
                new_target = float(input("Enter new target amount: "))
                c.execute("UPDATE savings_goals SET target_amount = ? WHERE id = ?", (new_target, goal_id))
            elif choice == 3:
                new_current = float(input("Enter new current amount: "))
                c.execute("UPDATE savings_goals SET current_amount = ? WHERE id = ?", (new_current, goal_id))
            elif choice == 4:
                new_deadline = input("Enter new deadline (YYYY-MM-DD): ").strip()
                datetime.datetime.strptime(new_deadline, "%Y-%m-%d")  # validate
                c.execute("UPDATE savings_goals SET deadline = ? WHERE id = ?", (new_deadline, goal_id))
            elif choice == 5:
                new_cat = int(input("Enter new category ID: "))
                if category_exists(new_cat):
                    c.execute("UPDATE savings_goals SET category_id = ? WHERE id = ?", (new_cat, goal_id))
                else:
                    print("Category does not exist.")
                    continue
            else:
                print("Please enter a number between 1 and 5.")
                continue

            conn.commit()
            print("\nSavings goal updated.")

            # Fetch updated goal and show dashboard-style summary
            c.execute("""
                SELECT id, name, target_amount, current_amount, deadline, created_at
                FROM savings_goals WHERE id = ?
            """, (goal_id,))
            goal = c.fetchone()
            if goal:
                sid, name, target, current, deadline, created_at = goal
                target = float(target or 0)
                current = float(current or 0)
                progress = (current / target * 100) if target > 0 else 0
                remaining = target - current

                bar_length = 20
                filled = int(bar_length * progress / 100)
                bar = "█" * filled + "░" * (bar_length - filled)

                deadline_date = datetime.datetime.strptime(deadline, "%Y-%m-%d")
                months_left = max(1, (deadline_date.year - datetime.date.today().year) * 12 +
                                     (deadline_date.month - datetime.date.today().month))
                required_monthly = remaining / months_left if remaining > 0 else 0
                state = "On track" if progress >= (100 * (datetime.date.today().month / 12)) else "Behind schedule"

                print(f"\n{name} (ID: {sid})")
                print(f"${current:.2f} / ${target:.2f}")
                print(f"{bar} {progress:.0f}%")
                print(f"Remaining: ${remaining:.2f}")
                print(f"Deadline: {deadline}")
                print(f"Created At: {created_at[:10]}")
                print(f"Required Monthly Contribution: ${required_monthly:.2f}")
                print(f"Status: {state}")

            break
        except ValueError:
            print("Invalid input. Please enter a number between 1 and 5.")

    conn.close()


def search_savings_goal():
    conn = sqlite3.connect('database/finance.db')
    c = conn.cursor()

    # Ask for ID and validate
    while True:
        try:
            goal_id = int(input("What is the ID of the savings goal you want to search: "))
            # Check if goal exists
            c.execute("SELECT id FROM savings_goals WHERE id = ?", (goal_id,))
            result = c.fetchone()
            if result is None:
                print("Invalid ID. Savings goal does not exist.\n")
                continue
            break
        except ValueError:
            print("Invalid input. Please enter a valid number.")

    # Fetch savings goal details
    c.execute("""
        SELECT id, name, target_amount, current_amount, deadline, created_at
        FROM savings_goals
        WHERE id = ?
    """, (goal_id,))

    goal = c.fetchone()
    if goal:
        sid = goal[0]
        name = goal[1]
        target = float(goal[2] or 0)
        current = float(goal[3] or 0)
        deadline = goal[4]
        created_at_str = goal[5][:10]

        progress = (current / target * 100) if target > 0 else 0
        remaining = target - current

        # Progress bar
        bar_length = 20
        filled = int(bar_length * progress / 100)
        bar = "█" * filled + "░" * (bar_length - filled)

        # Required monthly contribution
        deadline_date = datetime.datetime.strptime(deadline, "%Y-%m-%d")
        months_left = max(1, (deadline_date.year - datetime.date.today().year) * 12 +
                             (deadline_date.month - datetime.date.today().month))
        required_monthly = remaining / months_left if remaining > 0 else 0

        # On-track status (simple heuristic)
        state = "On track" if progress >= (100 * (datetime.date.today().month / 12)) else "Behind schedule"

        print("\n==== Savings Goal Details ====\n")
        print(f"{name} (ID: {sid})")
        print(f"${current:.2f} / ${target:.2f}")
        print(f"{bar} {progress:.0f}%")
        print(f"Remaining: ${remaining:.2f}")
        print(f"Deadline: {deadline}")
        print(f"Created At: {created_at_str}")
        print(f"Required Monthly Contribution: ${required_monthly:.2f}")
        print(f"Status: {state}")

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
        print("\n==== Savings Goals Menu ====")
        print("1: Add Savings Goal")
        print("2: View/Filter Savings Goals")
        print("3: Search Savings Goal by ID")
        print("4: Financial Actions (update/delete)")
        print("5: Add Money to Savings Goal")
        print("0: Back to Dashboard")

        try:
            choice = int(input("Select an option: "))
            if choice == 1:
                add_savings_goal()
            elif choice == 2:
                while True:
                    print("\n==== View/Filter Savings Goals ====")
                    print("1: View all savings goals")
                    print("2: Search by keyword")
                    print("3: Filter by deadline range (manual)")
                    print("4: Quick date range selector")  # new option
                    print("5: Sort by deadline")
                    print("6: Sort by target amount")
                    print("7: Sort by current amount")
                    print("0: Back")

                    sub_choice = input("Select an option: ").strip()

                    if sub_choice == "1":
                        filter_savings_goals("all")
                    elif sub_choice == "2":
                        filter_savings_goals("keyword")
                    elif sub_choice == "3":
                        filter_savings_goals("date")
                    elif sub_choice == "4":
                        filter_savings_goals("range")  # new mode
                    elif sub_choice == "5":
                        filter_savings_goals("sort_deadline")
                    elif sub_choice == "6":
                        filter_savings_goals("sort_target")
                    elif sub_choice == "7":
                        filter_savings_goals("sort_current")
                    elif sub_choice == "0":
                        break
                    else:
                        print("Invalid choice. Please enter 0–7.")

            elif choice == 3:
                search_savings_goal()
            elif choice == 4:
                financial_actions()
            elif choice == 5:
                add_money_to_goal()
            elif choice == 0:
                break
            else:
                print("Invalid choice. Please enter 0–4.")
        except ValueError:
            print("Invalid input. Please enter a number.")