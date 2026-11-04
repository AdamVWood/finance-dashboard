-- Personal Budget & Investment Dashboard - database schema
--
-- Conventions
--   * All money amounts are stored as INTEGER cents (e.g. $12.34 -> 1234) to
--     avoid floating-point rounding errors. Investment unit prices and
--     quantities are REAL because they legitimately need sub-cent precision
--     (fractional shares, crypto).
--   * Dates are ISO-8601 text: 'YYYY-MM-DD'.
--   * Liability account balances are stored as negative numbers (money owed).

PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS settings (
    key   TEXT PRIMARY KEY,
    value TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS categories (
    id          INTEGER PRIMARY KEY,
    name        TEXT    NOT NULL COLLATE NOCASE,
    kind        TEXT    NOT NULL CHECK (kind IN ('income', 'expense')),
    color       TEXT,
    is_archived INTEGER NOT NULL DEFAULT 0,
    created_at  TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (name, kind)
);

CREATE TABLE IF NOT EXISTS accounts (
    id                    INTEGER PRIMARY KEY,
    name                  TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    type                  TEXT    NOT NULL CHECK (type IN (
                              'cash', 'checking', 'savings', 'other_asset',
                              'credit_card', 'loan', 'other_liability')),
    institution           TEXT,
    opening_balance_cents INTEGER NOT NULL DEFAULT 0,
    opened_on             TEXT    NOT NULL,
    is_archived           INTEGER NOT NULL DEFAULT 0,
    notes                 TEXT,
    created_at            TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS recurring (
    id            INTEGER PRIMARY KEY,
    description   TEXT    NOT NULL,
    type          TEXT    NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    amount_cents  INTEGER NOT NULL CHECK (amount_cents > 0),
    account_id    INTEGER NOT NULL REFERENCES accounts (id) ON DELETE CASCADE,
    to_account_id INTEGER REFERENCES accounts (id) ON DELETE CASCADE,
    category_id   INTEGER REFERENCES categories (id) ON DELETE RESTRICT,
    frequency     TEXT    NOT NULL CHECK (frequency IN (
                      'weekly', 'biweekly', 'monthly', 'quarterly', 'yearly')),
    start_date    TEXT    NOT NULL,   -- anchor date; occurrences are counted from here
    next_date     TEXT    NOT NULL,   -- next occurrence not yet posted
    end_date      TEXT,
    is_active     INTEGER NOT NULL DEFAULT 1,
    notes         TEXT,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((type = 'transfer' AND to_account_id IS NOT NULL AND category_id IS NULL
            AND to_account_id <> account_id)
        OR (type <> 'transfer' AND to_account_id IS NULL AND category_id IS NOT NULL))
);

CREATE TABLE IF NOT EXISTS transactions (
    id            INTEGER PRIMARY KEY,
    date          TEXT    NOT NULL,
    description   TEXT    NOT NULL,
    type          TEXT    NOT NULL CHECK (type IN ('income', 'expense', 'transfer')),
    amount_cents  INTEGER NOT NULL CHECK (amount_cents > 0),
    account_id    INTEGER NOT NULL REFERENCES accounts (id) ON DELETE RESTRICT,
    to_account_id INTEGER REFERENCES accounts (id) ON DELETE RESTRICT,
    category_id   INTEGER REFERENCES categories (id) ON DELETE RESTRICT,
    notes         TEXT,
    recurring_id  INTEGER REFERENCES recurring (id) ON DELETE SET NULL,
    created_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at    TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP,
    CHECK ((type = 'transfer' AND to_account_id IS NOT NULL AND category_id IS NULL
            AND to_account_id <> account_id)
        OR (type <> 'transfer' AND to_account_id IS NULL AND category_id IS NOT NULL))
);

CREATE INDEX IF NOT EXISTS ix_transactions_date ON transactions (date);
CREATE INDEX IF NOT EXISTS ix_transactions_category ON transactions (category_id, date);
CREATE INDEX IF NOT EXISTS ix_transactions_account ON transactions (account_id, date);
CREATE INDEX IF NOT EXISTS ix_transactions_to_account ON transactions (to_account_id, date);

CREATE TABLE IF NOT EXISTS budgets (
    id           INTEGER PRIMARY KEY,
    category_id  INTEGER NOT NULL REFERENCES categories (id) ON DELETE CASCADE,
    year         INTEGER NOT NULL CHECK (year BETWEEN 1990 AND 2100),
    month        INTEGER NOT NULL CHECK (month BETWEEN 1 AND 12),
    amount_cents INTEGER NOT NULL CHECK (amount_cents >= 0),
    UNIQUE (category_id, year, month)
);

CREATE TABLE IF NOT EXISTS savings_goals (
    id           INTEGER PRIMARY KEY,
    name         TEXT    NOT NULL UNIQUE COLLATE NOCASE,
    target_cents INTEGER NOT NULL CHECK (target_cents > 0),
    start_date   TEXT    NOT NULL,
    deadline     TEXT,
    notes        TEXT,
    is_archived  INTEGER NOT NULL DEFAULT 0,
    created_at   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS goal_contributions (
    id           INTEGER PRIMARY KEY,
    goal_id      INTEGER NOT NULL REFERENCES savings_goals (id) ON DELETE CASCADE,
    date         TEXT    NOT NULL,
    amount_cents INTEGER NOT NULL CHECK (amount_cents <> 0),
    note         TEXT,
    created_at   TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE INDEX IF NOT EXISTS ix_goal_contributions_goal ON goal_contributions (goal_id, date);

CREATE TABLE IF NOT EXISTS investments (
    id             INTEGER PRIMARY KEY,
    name           TEXT    NOT NULL,
    ticker         TEXT,
    asset_type     TEXT    NOT NULL CHECK (asset_type IN (
                       'stock', 'etf', 'mutual_fund', 'bond', 'crypto',
                       'real_estate', 'cash_equivalent', 'other')),
    quantity       REAL    NOT NULL CHECK (quantity > 0),
    purchase_price REAL    NOT NULL CHECK (purchase_price >= 0),
    purchase_date  TEXT    NOT NULL,
    current_price  REAL,
    price_date     TEXT,
    funding_account_id  INTEGER REFERENCES accounts (id) ON DELETE RESTRICT,  -- cash account the purchase came from
    sold_on             TEXT,                                                 -- set when the holding is sold
    sale_price          REAL CHECK (sale_price IS NULL OR sale_price >= 0),
    proceeds_account_id INTEGER REFERENCES accounts (id) ON DELETE RESTRICT,  -- account the sale proceeds went to
    notes          TEXT,
    created_at     TEXT    NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS investment_prices (
    id            INTEGER PRIMARY KEY,
    investment_id INTEGER NOT NULL REFERENCES investments (id) ON DELETE CASCADE,
    date          TEXT    NOT NULL,
    price         REAL    NOT NULL CHECK (price >= 0),
    UNIQUE (investment_id, date)
);
