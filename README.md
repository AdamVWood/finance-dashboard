# Personal Budget & Investment Dashboard

A private, self-hosted web app for managing your money in one place: accounts, income and
expenses, budgets, savings goals, investments, recurring bills and net worth, with charts and reports.

It runs on your own computer. Your data stays in a single SQLite file and nothing is sent anywhere.

![Dashboard](docs/screenshots/dashboard.png)

---

## Quick start

Requirements: **Python 3.10 or newer**. Flask is the only dependency.

```bash
cd finance-dashboard
python -m venv .venv
# Windows:  .venv\Scripts\activate
# macOS/Linux:  source .venv/bin/activate
pip install -r requirements.txt
python run.py
```

Then open **http://127.0.0.1:5000** in your browser.

The database is created on first run at `instance/finance.db`, with a starter set of income and
expense categories.

**Just exploring?** On the empty dashboard, click **Load 12 months of sample data**, or run
`flask --app run seed-demo`. When you're ready to start for real, go to **Settings → Erase all data**.

### Getting started with your own data

1. **Accounts:** add every account (chequing, savings, cash, credit cards, loans) with its balance on a given date.
2. **Transactions:** record them one at a time, or import a CSV exported from your bank (*Transactions → Import*).
3. **Recurring:** add your salary, rent, phone bill and subscriptions. When one falls due, the dashboard offers to post it.
4. **Budgets:** set monthly limits per expense category. *Copy from last month* and *3-month averages* make this quick.
5. **Savings goals:** add targets with deadlines and record money as you set it aside.
6. **Investments:** add holdings, optionally saying which account paid for them, and update prices now and then.

---

## Features

| Area | What it does |
|---|---|
| **Dashboard** | Income, expenses, net savings, savings rate and net worth for this month, last month, the last 3 months, this year or the last 12 months, with changes vs the previous period. Charts for income vs expenses, spending by category and net worth. Also shows budget status, goals, portfolio, accounts, recent transactions, upcoming bills and a "due now" banner. |
| **Transactions** | Income, expenses and **transfers** between your own accounts (transfers are never counted as income or spending). Search; filter by type, category, account, date range and amount range; sort; page through results; totals for whatever is filtered. Edit, duplicate, delete, or select several and delete together. CSV import (all-or-nothing, with row-by-row error messages) and export. |
| **Accounts & net worth** | Asset and liability accounts. Balances are always calculated from transactions, so they can't drift. Net worth = cash + investments − debts, with a 12-month history calculated from your records (no snapshots needed). |
| **Budgets** | Monthly budget per expense category, with spent, remaining, progress and status (on track / near limit at 80% / fully used / over). Shows unbudgeted spending. Move between months, copy last month's budgets, or fill from 3-month averages. |
| **Savings goals** | Target, optional deadline, a full history of money added and withdrawn, progress %, amount remaining, amount needed per month, an on-track check against an even saving plan, and an estimated finish date at your recent pace. |
| **Investments** | Holdings with cost, value, profit/loss and return %, allocation by asset type, manual and bulk price updates with a price history and value chart, sales with realised gains, and an optional link to the account that paid for each purchase. |
| **Recurring** | Weekly, fortnightly, monthly, quarterly or yearly items with optional end dates. Due items are posted only when you choose. You can also skip an occurrence or pause an item. Shows regular monthly income vs bills. |
| **Reports** | Yearly totals vs the previous year, monthly income/expense/net/savings-rate table and charts, spending by category for any date range, a category × month table, and budget vs actual for the year. CSV downloads. |
| **Settings & backup** | Currency (defaults to BBD), your name, one-click backup download, restore from a backup, sample data, and erase all data. Restore and erase save a safety copy first. |
| **Interface** | Responsive (phone to desktop), light and dark mode, keyboard accessible, a "show as table" option for charts, helpful empty states, and validation messages next to the field that needs fixing. |

---

## Project structure

```
finance-dashboard/
├── run.py                  # start the app
├── requirements.txt
├── finance/
│   ├── __init__.py         # app factory: config, security, template filters, error pages
│   ├── db.py               # per-request SQLite connection, schema setup and migrations
│   ├── schema.sql          # database schema (tables, constraints, indexes)
│   ├── utils.py            # money parsing/formatting, date helpers, form Validator
│   ├── cli.py              # flask commands: init-db, seed-demo, backup, import-legacy
│   ├── demo.py             # sample data generator
│   ├── legacy.py           # importer for the original version's database
│   ├── services/           # business logic, one module per area (no Flask request code)
│   │   ├── accounts.py  transactions.py  categories.py  budgets.py
│   │   ├── goals.py  investments.py  recurring.py  reports.py  settings.py
│   ├── views/              # Flask blueprints (thin: parse request -> call service -> render)
│   ├── templates/          # Jinja templates; partials/macros.html holds shared UI pieces
│   └── static/
│       ├── css/app.css     # the full design system (tokens, components, light/dark)
│       └── js/             # app.js (behaviour), charts.js (built-in SVG charts), theme.js
├── tests/                  # pytest suite (53 tests)
└── instance/               # created at runtime: finance.db, secret_key, backups/, app.log
```

**Layers:** *views* handle HTTP only; *services* hold every rule and calculation; *db.py*
owns the connection. A feature change usually touches one service, one view and one template.

---

## Data model

```
accounts ─┬─< transactions >── categories ──< budgets (one per category per month)
          │        └─ recurring (optional link to the item that created it)
          ├─< recurring
          └─< investments (funding_account_id / proceeds_account_id) ──< investment_prices

savings_goals ──< goal_contributions
settings (key/value)
```

* **Money is stored as whole cents (integers)**, so totals never pick up floating-point errors.
  Only investment unit prices and quantities are decimals, because fractional shares and crypto need them.
* **Transaction types** are `income`, `expense` and `transfer`. Database CHECK constraints make a
  transfer always have a destination account and no category, and make income and expenses always have a category.
* **Liabilities** (credit cards, loans) are stored as negative balances. On forms you enter the amount owed as a positive number.
* **Savings goals** don't move money and aren't added to net worth. They earmark money that's already in your accounts.

### Changing the schema later

`PRAGMA user_version` stores the schema version (`SCHEMA_VERSION` in `finance/db.py`).
To add a column, increase `SCHEMA_VERSION` and add a step in `init_schema()`, for example:

```python
if version < 2:
    conn.execute("ALTER TABLE accounts ADD COLUMN colour TEXT")
```

The step runs automatically the next time the app starts.

---

## Maintenance

| Task | How |
|---|---|
| Back up | *Settings → Download backup*, or `flask --app run backup [path]`. Keep copies off your computer (OneDrive, Google Drive). |
| Restore | *Settings → Restore* (type `RESTORE` to confirm). |
| Run tests | `pip install pytest` then `python -m pytest` |
| Move your data | Copy `instance/finance.db` (with the app stopped), or use a backup file. |
| Use a different database file | Set `FINANCE_DB=/path/to/file.db` before starting the app. |
| Logs | Warnings and errors are written to `instance/app.log` (rotated automatically). |
| Debug mode | `FLASK_DEBUG=1 python run.py` (auto-reload while you edit code; never use it on a network). |

### Bringing over data from the original version

The original app stored its data in `database/finance.db`. To import it:

```bash
flask --app run import-legacy "path/to/old/database/finance.db"
```

Old `Deposit` transactions become income. Every other old type (Withdrawal, Direct Debit, Fee,
Remittance, Transfer) becomes an expense, all in one account called "Imported account", because the old
version had no accounts. Review them afterwards and recategorise any that were really transfers. Goals keep
their saved amount, and budgets and investments carry over as they are.

---

## Security notes

* The app has **no login** because it's designed for one person on one computer. It only listens on `127.0.0.1`,
  so other devices on your network can't reach it. Don't expose it to the internet as it stands.
  Adding accounts and logins is listed under limitations below.
* Every form is protected against CSRF, and security headers (Content-Security-Policy, X-Frame-Options and others) are sent.
* All SQL uses parameters, and every input is checked on the server, not just in the browser.
* A random secret key is generated on first run and saved in `instance/secret_key`. Set `SECRET_KEY` to override it.

---

## Limitations and possible next steps

* **Live investment prices** need an external market-data service, usually with an API key and rate limits.
  For now prices are entered by hand (bulk update on *Investments → Update prices*), and every update is kept so history and charts still work.
  The place to plug in a provider is `investments.update_prices()`.
* **One currency.** Multi-currency accounts would need exchange rates.
* **Partial sales:** to sell part of a holding, reduce its quantity and add the sold part as a separate holding, then mark that one as sold.
* **No bank sync.** Use CSV import with your bank's statement export.
* **Single user, no login.** Adding Flask-Login with per-user data would be the next step if it ever needs to run on a server.
