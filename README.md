# Planned Enhancements

## 1. Budgets
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

## 2. Savings Goals
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


## 3. User Experience
- Add a FAQ page to improve onboarding and answer common questions.
- Enable Excel integration:
- **Export**: Generate a sheet for easier bulk data entry.
- **Import**: Load that sheet back into the system to populate the database.
- Gracefully handle empty databases by skipping queries and continuing without errors.