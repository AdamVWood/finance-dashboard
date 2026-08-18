from app import transactions, budgets, savings_goals, investments, categories, financial_report


def main_menu():
    while True:
        print("\n==== Finance Dashboard ====")
        print("1: Manage Transactions")
        print("2: Manage Budgets")
        print("3: Manage Savings Goals")
        print("4: Manage Investments")
        print("5: Manage Categories")
        print("6: Financial Reports")
        print("0: Exit")

        try:
            choice = int(input("Select an option: "))
            if choice == 1:
                transactions.menu()
            elif choice == 2:
                budgets.menu()
            elif choice == 3:
                savings_goals.menu()
            elif choice == 4:
                investments.menu()
            elif choice == 5:
                categories.menu()
            elif choice == 6:
                financial_report.menu()
            elif choice == 0:
                print("Goodbye!")
                break
            else:
                print("Invalid choice. Please enter a number between 0 and 6.")
        except ValueError:
            print("Invalid input. Please enter a number.")

