# Planned Enhancements

## 1. Investments
- Standardize asset types to:
Stock
ETF
Bond
Crypto
Other

Code

## 2. Transactions
- Add full edit/delete functionality for every transaction.
- Require confirmation before deletion.
- Implement a date range selector:
This Month
Last Month
Last 3 Months
This Year
All Time

Code

## 3. Budgets
- Redesign budget tracking to show progress visually:
Food
$372 / $500
██████████████░░░░
74%

Code
- Define budget states programmatically:
- **Under budget** (< 80%)
- **Near limit** (80–100%)
- **Over budget** (> 100%)
- Create a budget dashboard displaying:
- Total budget
- Total spent
- Remaining balance
- Percentage used
- Categories over budget
- Categories approaching their limits

## 4. Savings Goals
- Introduce a dedicated savings goals system.
- Each goal includes:
- Name
- Target amount
- Current amount
- Deadline
- Progress bar and percentage
- Example:

Emergency Fund

$2,500 / $5,000

██████████░░░░░░░░░░
50%

Deadline: December 2026

Code
- Add functionality to update the current amount and calculate:
- Remaining amount
- Percentage complete
- Required monthly contribution
- On-track status

## 5. Portfolio Overview / Financial Reports
- Redesign reporting to include:
- Total invested
- Current portfolio value
- Profit/loss
- Return percentage
- Number of holdings

## 6. User Experience
- Add a FAQ page to improve onboarding and answer common questions.
- Enable Excel integration:
- **Export**: Generate a sheet for easier bulk data entry.
- **Import**: Load that sheet back into the system to populate the database.
- Gracefully handle empty databases by skipping queries and continuing without errors.