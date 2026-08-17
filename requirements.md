
**Core areas**

* Transactions
* Budgets
* Savings goals
* Investments
* Dashboard
* Financial reports

Don't start coding immediately. First decide how everything connects.

### 2. Plan the database

Your Phase 2 database was relatively simple.

For Phase 4, I'd aim for something like:

```text
users
 └── transactions
      └── categories

users
 └── budgets
      └── categories

users
 └── savings_goals

users
 └── investments
```

Possible tables:

### `transactions`

* id
* amount
* transaction_type
* category_id
* description
* date
* created_at

### `categories`

* id
* name
* type

Examples:

```text
Food
Transportation
Entertainment
Bills
Education
Shopping
Salary
Other
```

### `budgets`

* id
* category_id
* amount
* month
* year

### `savings_goals`

* id
* name
* target_amount
* current_amount
* deadline
* created_at

### `investments`

* id
* name
* ticker
* asset_type
* quantity
* purchase_price
* purchase_date

You don't need every possible field immediately. Start with what the application actually needs.

### Day 1 deliverable

Before moving on, you should have:

* Database schema
* Table relationships
* Feature list
* Basic application structure
* Rough dashboard layout

---

# Day 2 — Backend Foundation

Build the Python side.

I'd recommend separating your code instead of putting everything into `main.py`.

Something like:

```text
finance-dashboard/
│
├── app/
│   ├── database.py
│   ├── models.py
│   ├── transactions.py
│   ├── budgets.py
│   ├── savings.py
│   └── investments.py
│
├── templates/
│   ├── index.html
│   ├── transactions.html
│   ├── budgets.html
│   ├── savings.html
│   └── investments.html
│
├── static/
│   ├── css/
│   │   └── style.css
│   └── js/
│       └── dashboard.js
│
├── database/
│   └── schema.sql
│
├── app.py
├── README.md
└── requirements.txt
```

You don't have to use exactly this structure, but I want you to start thinking about **separation of concerns**.

### Backend functionality

Create functions/routes for:

* Adding transactions
* Retrieving transactions
* Updating transactions
* Deleting transactions
* Adding budgets
* Retrieving budgets
* Updating budgets
* Adding savings goals
* Updating savings progress
* Adding investments
* Retrieving investments

This is where your Phase 2 experience should make things go quickly.

---

# Day 3 — Transaction System

Now rebuild your Finance Tracker's core functionality inside the web application.

## Transaction page

Users should be able to:

### Add transaction

Fields:

```text
Amount
Type
Category
Description
Date
```

Transaction types:

```text
Income
Expense
Transfer
```

I'd simplify your old transaction-type system for the website unless you have a specific reason to retain all six types.

### View transactions

Display something like:

| Date   | Description | Category | Type    | Amount |
| ------ | ----------- | -------- | ------- | -----: |
| Aug 10 | Groceries   | Food     | Expense |   $150 |
| Aug 9  | Salary      | Income   | Income  | $2,500 |

### Add:

* Search
* Category filter
* Type filter
* Date filter
* Sort by date
* Sort by amount

### Edit/delete

Every transaction should have:

* Edit
* Delete

And **deleting should require confirmation**.

---

# Day 4 — Dashboard

This is where the project starts becoming significantly different from your Phase 2 project.

Your homepage should be a proper financial dashboard.

## Top-level cards

Something like:

```text
┌──────────────┐ ┌──────────────┐ ┌──────────────┐
│ Total Income │ │Total Expenses│ │ Net Savings  │
│   $5,200     │ │   $3,100     │ │   $2,100     │
└──────────────┘ └──────────────┘ └──────────────┘
```

And:

```text
┌──────────────────────┐
│ Net Worth             │
│ $15,430               │
└──────────────────────┘
```

## Dashboard statistics

Calculate:

* Total income
* Total expenses
* Net savings
* Savings rate
* Total investment value
* Total savings
* Net worth

### Important

Don't hard-code these.

They should be calculated from your database.

---

# Day 5 — Financial Analytics

This is one of the most important parts of the project.

Add charts using JavaScript.

## Chart 1 — Income vs Expenses

A monthly chart:

```text
Income
Expenses
```

for several months.

---

## Chart 2 — Spending by Category

A pie/doughnut chart showing:

```text
Food
Bills
Transportation
Entertainment
Shopping
Other
```

This makes the dashboard actually useful.

---

## Chart 3 — Monthly Spending

A line/bar chart showing spending over time.

For example:

```text
March
April
May
June
July
August
```

---

## Chart 4 — Savings Progress

Show:

```text
Income
    ↓
Expenses
    ↓
Savings
```

and visualize the savings trend.

### Optional

Add a date range selector:

```text
This Month
Last Month
Last 3 Months
This Year
All Time
```

That would be a very nice feature.

---

# Day 6 — Budget System

Now introduce actual budgeting.

## Create budget

The user chooses:

```text
Category
Monthly Limit
Month
Year
```

Example:

```text
Food
Budget: $500
Spent: $372
Remaining: $128
```

## Budget progress

Display:

```text
Food

$372 / $500

██████████████░░░░
74%
```

### Budget states

Have the system identify:

**Under budget**

```text
$372 / $500
```

**Near limit**

```text
$470 / $500
```

**Over budget**

```text
$550 / $500
```

You can determine these programmatically.

For example:

* `< 80%` → healthy
* `80–100%` → warning
* `> 100%` → exceeded

You can choose your own thresholds.

### Budget dashboard

Show:

* Total budget
* Total spent
* Remaining
* Percentage used
* Categories over budget
* Categories approaching their limits

---

# Day 7 — Savings Goals

Add a dedicated **Savings Goals** system.

Users can create:

```text
Emergency Fund
Laptop
Car
University
Vacation
```

Each goal has:

* Goal name
* Target amount
* Current amount
* Deadline
* Progress

Example:

```text
Emergency Fund

$2,500 / $5,000

██████████░░░░░░░░░░

50%

Deadline:
December 2026
```

### Add money

Allow the user to update the current amount.

Calculate:

* Amount remaining
* Percentage complete
* Required monthly contribution
* Whether they're on track

That last one would be a particularly nice feature.

---

# Day 8 — Investment Portfolio

This is what turns the project from a simple budgeting application into a proper **Budget & Investment Dashboard**.

## Investment page

Allow users to record:

* Investment name
* Ticker
* Asset type
* Quantity
* Purchase price
* Purchase date

Asset types could include:

```text
Stock
ETF
Bond
Crypto
Other
```

### Portfolio overview

Display:

* Total invested
* Current portfolio value
* Profit/loss
* Return percentage
* Number of holdings

### Portfolio allocation

Create a chart showing:

```text
ETF       60%
Stocks    25%
Bonds     10%
Other      5%
```

### Individual holdings

Example:

| Asset | Quantity |   Cost |  Value | Return |
| ----- | -------: | -----: | -----: | -----: |
| ETF   |       10 | $1,000 | $1,150 |   +15% |
| Stock |        5 |   $500 |   $540 |    +8% |

---

# Day 9 — Net Worth + Polish

Now connect everything together.

## Net worth

Conceptually:

**Assets − Liabilities = Net Worth**

Your assets could include:

* Cash
* Savings
* Investments

You could optionally add liabilities such as:

* Credit card debt
* Loans
* Other debt

Then display:

```text
Net Worth

$18,450
```

And ideally show its change over time.

### Net-worth history

Something like:

```text
April     $12,000
May       $13,500
June      $15,200
July      $17,100
August    $18,450
```

Then turn that into a line chart.

---

# Day 10 — Professionalization

This day is extremely important.

Don't just stop when the application technically works.

## UI

Make sure the website has:

* Consistent navigation
* Consistent spacing
* Good typography
* Cards/components
* Responsive design
* Mobile support
* Clear buttons
* Form validation
* Error messages
* Empty states

Example:

Instead of an empty transaction table simply showing nothing:

> **No transactions found.**
> Add your first transaction to start tracking your finances.

That's the sort of polish that makes an application feel professional.

---

# Features I Consider "Must Have"

Don't move on from Phase 4 without these:

### Core

* [ ] SQLite database
* [ ] Python backend
* [ ] HTML
* [ ] CSS
* [ ] JavaScript
* [ ] CRUD transactions
* [ ] Categories
* [ ] Search/filter transactions

### Dashboard

* [ ] Income
* [ ] Expenses
* [ ] Net savings
* [ ] Savings rate
* [ ] Net worth
* [ ] Financial summary

### Analytics

* [ ] Spending by category
* [ ] Income vs expenses
* [ ] Spending over time
* [ ] Savings trend

### Budgeting

* [ ] Create budgets
* [ ] Track spending against budgets
* [ ] Budget progress
* [ ] Over-budget detection

### Savings

* [ ] Create goals
* [ ] Track progress
* [ ] Amount remaining
* [ ] Deadline
* [ ] Progress percentage

### Investments

* [ ] Add investments
* [ ] Track holdings
* [ ] Portfolio value
* [ ] Profit/loss
* [ ] Portfolio allocation

### Quality

* [ ] Input validation
* [ ] Error handling
* [ ] Responsive design
* [ ] Clean project structure
* [ ] README
* [ ] Screenshots
* [ ] Good Git history

---

# Features I'd Put in the "If I Have Time" Category

These are **not required** for your 1½-week target.

### Authentication

* User registration
* Login
* Password hashing
* User-specific data

### CSV

* Export transactions to CSV
* Import transactions from CSV

### Advanced filtering

* Custom date ranges
* Multiple categories
* Amount ranges

### Recurring transactions

For things like:

```text
Monthly salary
Rent
Subscriptions
Phone bill
```

### Dark mode

Nice for the website, but not necessary.

### API integration

You could eventually retrieve live investment prices.

But **don't let this derail the project**.

---

# What I DON'T Want You Doing

This is important because you could easily turn this into a huge project.

I **wouldn't** add:

* Complex banking integrations
* Real bank account connections
* Real payment processing
* AI financial advice
* Cryptocurrency trading
* Complicated authentication systems
* Huge amounts of animations
* 20 different charts
* A mobile app
* Cloud infrastructure
* Microservices

Those aren't necessary to prove that you can build a strong application.

---

# Your Final Project Stack

I'd like your finished project to roughly demonstrate:

```text
                    ┌─────────────────────┐
                    │      Frontend       │
                    │   HTML / CSS / JS   │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │       Backend       │
                    │       Python        │
                    └──────────┬──────────┘
                               │
                               ▼
                    ┌─────────────────────┐
                    │      Database       │
                    │       SQLite        │
                    └─────────────────────┘
```

And your application sits on top of all of that:

```text
                 PERSONAL FINANCE DASHBOARD
                           │
       ┌───────────────────┼───────────────────┐
       │                   │                   │
 Transactions           Budgets            Savings
       │                   │                   │
       └───────────────────┼───────────────────┘
                           │
                     Investments
                           │
                           ▼
                     Dashboard
                           │
               ┌───────────┼───────────┐
               │           │           │
            Charts      Analytics    Net Worth
```

## The most important distinction

Your Phase 2 project demonstrated:

> **"I can build a database application."**

Your Phase 4 project should demonstrate:

> **"I can design and build a complete software application using multiple technologies."**

That's a **much stronger portfolio story**.

And because you've already done the Finance Tracker, Inventory Management System, and your web-development phase, I genuinely think **10–11 focused days is a reasonable target for you**. The challenge isn't learning the basics anymore; it's putting everything together cleanly and making the final product polished.
