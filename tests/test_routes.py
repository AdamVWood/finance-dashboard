import io
import sqlite3

from finance import create_app
from finance.services import transactions

from .conftest import add_txn

PAGES = ["/", "/transactions/", "/transactions/new", "/transactions/import", "/accounts/", "/accounts/new",
         "/categories/", "/budgets/", "/goals/", "/goals/new", "/investments/", "/investments/new",
         "/investments/prices", "/recurring/", "/recurring/new", "/reports/", "/settings/"]


def test_every_page_renders_when_empty(client):
    for url in PAGES:
        assert client.get(url).status_code == 200, url


def test_every_page_renders_with_demo_data(client):
    from finance.demo import seed_demo
    seed_demo()
    for url in PAGES + ["/accounts/1", "/accounts/1/edit", "/goals/1", "/investments/1", "/recurring/1/edit",
                        "/transactions/1/edit", "/categories/1/edit", "/budgets/?edit=1", "/?period=this_year",
                        "/reports/?year=2025", "/transactions/?q=fuel&period=last_3_months&sort=amount_desc"]:
        assert client.get(url).status_code == 200, url


def test_missing_records_404(client):
    assert client.get("/transactions/999/edit").status_code == 404
    assert client.get("/goals/999").status_code == 404


def test_add_transaction_through_form(client, setup):
    r = client.post("/transactions/new", data={"type": "expense", "amount": "12.50", "description": "Lunch",
                                               "date": "2026-02-01", "account_id": setup["chq"],
                                               "category_id": setup["dining"]})
    assert r.status_code == 302
    assert transactions.search({})["count"] == 1


def test_invalid_form_shows_errors_and_keeps_input(client, setup):
    r = client.post("/transactions/new", data={"type": "expense", "amount": "abc", "description": "Kept text",
                                               "date": "", "account_id": setup["chq"]})
    assert r.status_code == 422
    assert b"Kept text" in r.data and b"valid number" in r.data


def test_csrf_blocks_posts_without_token(tmp_path):
    app = create_app({"TESTING": True, "SECRET_KEY": "x", "DATABASE": str(tmp_path / "c.db"),
                      "BACKUP_DIR": str(tmp_path / "b")})
    client = app.test_client()
    r = client.post("/accounts/new", data={"name": "A", "type": "cash"})
    assert r.status_code == 302  # rejected and redirected with a message
    with app.app_context():
        from finance.db import get_db
        assert get_db().execute("SELECT COUNT(*) FROM accounts").fetchone()[0] == 0
    client.get("/")
    with client.session_transaction() as s:
        token = s["_csrf"]
    r = client.post("/accounts/new", data={"name": "A", "type": "cash", "_csrf": token})
    assert r.status_code == 302 and r.headers["Location"].endswith("/accounts/")


def test_backup_and_restore_round_trip(client, setup, tmp_path):
    add_txn(setup, "expense", 10, "2026-02-01", category="groceries")
    backup = client.get("/settings/backup")
    assert backup.status_code == 200 and backup.data[:15] == b"SQLite format 3"
    add_txn(setup, "expense", 20, "2026-02-02", category="groceries")
    assert transactions.search({})["count"] == 2
    r = client.post("/settings/restore", data={"confirm": "RESTORE",
                                               "file": (io.BytesIO(backup.data), "backup.db")},
                    content_type="multipart/form-data")
    assert r.status_code == 302
    assert transactions.search({})["count"] == 1


def test_restore_rejects_other_files(client):
    r = client.post("/settings/restore", data={"confirm": "RESTORE", "file": (io.BytesIO(b"hello"), "x.db")},
                    content_type="multipart/form-data", follow_redirects=True)
    assert b"isn&#39;t a valid backup" in r.data or b"isn't a valid backup" in r.data


def test_reset_requires_confirmation(client, setup):
    client.post("/settings/reset", data={"confirm": "nope"})
    assert b">Chequing</a>" in client.get("/accounts/").data
    client.post("/settings/reset", data={"confirm": "DELETE"})
    assert b">Chequing</a>" not in client.get("/accounts/").data


def test_legacy_import(app, tmp_path):
    path = tmp_path / "old.db"
    old = sqlite3.connect(path)
    old.executescript("""
        CREATE TABLE categories (id INTEGER PRIMARY KEY, name TEXT);
        CREATE TABLE transactions (id INTEGER PRIMARY KEY, amount REAL, transaction_type TEXT, category_id INT,
                                   description TEXT, date TEXT, created_at TEXT);
        CREATE TABLE savings_goals (id INTEGER PRIMARY KEY, name TEXT, target_amount REAL, current_amount REAL,
                                    deadline TEXT, created_at TEXT, category_id INT);
        INSERT INTO categories VALUES (1, 'Food'), (2, 'Work');
        INSERT INTO transactions VALUES (1, 25.5, 'Withdrawal', 1, 'Lunch', '2026-01-03', NULL),
                                        (2, 1000, 'Deposit', 2, 'Pay', '2026-01-25', NULL);
        INSERT INTO savings_goals VALUES (1, 'Car', 5000, 1200, '2027-01-01', '2026-01-01', 1);
    """)
    old.commit()
    old.close()
    from finance.legacy import import_legacy
    from finance.services import goals
    counts = import_legacy(str(path))
    assert counts["transactions"] == 2 and counts["goals"] == 1
    result = transactions.search({})
    assert result["income_cents"] == 100000 and result["expense_cents"] == 2550
    assert goals.list_goals()[0]["saved_cents"] == 120000
