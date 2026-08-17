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