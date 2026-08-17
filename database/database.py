import sqlite3

def setup():
    conn = sqlite3.connect("database/finance.db")
    c = conn.cursor()
    # Enable foreign keys
    c.execute("PRAGMA foreign_keys = ON;")
    # Create transactions table
    c.execute("""
        CREATE TABLE IF NOT EXISTS transactions (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- Unique identifier
            amount REAL NOT NULL,                 -- Numeric amount
            transaction_type TEXT NOT NULL,       -- Income / Expense / Transfer
            category_id INTEGER NOT NULL,         -- Foreign key to categories
            description TEXT,                     -- Optional details
            date TEXT NOT NULL,                   -- YYYY-MM-DD format
            created_at TEXT DEFAULT CURRENT_TIMESTAMP -- Auto timestamp
        );
    """)

    # Create categories table
    c.execute("""
        CREATE TABLE IF NOT EXISTS categories (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- Unique identifier
            name TEXT NOT NULL UNIQUE        -- Income / Expense / Other
        );
    """)

    # Create budgets table
    c.execute("""
        CREATE TABLE IF NOT EXISTS budgets (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- Unique identifier
            category_id INTEGER NOT NULL,         -- Foreign key to categories
            amount REAL NOT NULL,                 -- Budgeted amount
            month INTEGER NOT NULL,               -- 1–12
            year INTEGER NOT NULL                 -- Four-digit year
            created_at TEXT DEFAULT CURRENT_TIMESTAMP -- Auto timestamp
        );
    """)

    # Create savings_goals table
    c.execute("""
        CREATE TABLE IF NOT EXISTS savings_goals (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- Unique identifier
            name TEXT NOT NULL UNIQUE,            -- Goal name (Emergency Fund, Car, etc.)
            target_amount REAL NOT NULL,          -- Target savings
            current_amount REAL NOT NULL DEFAULT 0, -- Progress so far
            deadline TEXT,                        -- YYYY-MM-DD
            created_at TEXT DEFAULT CURRENT_TIMESTAMP -- Auto timestamp
        );
    """)

    # Create investments table
    c.execute("""
        CREATE TABLE IF NOT EXISTS investments (
            id INTEGER PRIMARY KEY AUTOINCREMENT, -- Unique identifier
            name TEXT NOT NULL,                   -- Investment name
            ticker TEXT,                          -- Stock/ETF symbol
            asset_type TEXT NOT NULL,             -- Stock / ETF / Bond / Crypto
            quantity REAL NOT NULL,               -- Number of units
            purchase_price REAL NOT NULL,         -- Price per unit
            purchase_date TEXT NOT NULL           -- YYYY-MM-DD
        );
    """)

    # #Insert sample categories
    # c.executemany(
    #     "INSERT OR IGNORE INTO categories (name) VALUES (?)",
    #     [("Electronics",), ("Food",), ("Clothing",)]
    # )
    # # Insert sample products (assuming IDs 1,2,3 match categories above)
    # c.executemany(
    #     """
    #     INSERT OR IGNORE INTO products (name, price, quantity, category_id)
    #     VALUES (?, ?, ?, ?)
    #     """,
    #     [
    #         ("Laptop", 1200.00, 10, 1),
    #         ("Bread", 2.50, 50, 2),
    #         ("Shirt", 25.00, 20, 3),
    #     ]
    # )

    conn.commit()
    conn.close()