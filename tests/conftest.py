import pytest

from finance import create_app
from finance.db import get_db


@pytest.fixture
def app(tmp_path):
    app = create_app({
        "TESTING": True,
        "CSRF_DISABLED": True,
        "SECRET_KEY": "test",
        "DATABASE": str(tmp_path / "test.db"),
        "BACKUP_DIR": str(tmp_path / "backups"),
    })
    with app.test_request_context():
        yield app


@pytest.fixture
def client(app):
    return app.test_client()


@pytest.fixture
def db(app):
    return get_db()


def cat_id(db, name, kind="expense"):
    return db.execute("SELECT id FROM categories WHERE name = ? AND kind = ?", (name, kind)).fetchone()["id"]


@pytest.fixture
def setup(db):
    """Two asset accounts and a credit card, opened on 2026-01-01."""
    from finance.services import accounts
    ids = {
        "chq": accounts.create_account({"name": "Chequing", "type": "checking", "opening_balance": "1000",
                                        "opened_on": "2026-01-01"}),
        "sav": accounts.create_account({"name": "Savings", "type": "savings", "opening_balance": "5000",
                                        "opened_on": "2026-01-01"}),
        "card": accounts.create_account({"name": "Card", "type": "credit_card", "opening_balance": "200",
                                         "opened_on": "2026-01-01"}),
        "groceries": cat_id(db, "Groceries"),
        "dining": cat_id(db, "Dining out"),
        "salary": cat_id(db, "Salary", "income"),
    }
    return ids


def add_txn(ids, type_, amount, date, account="chq", category=None, to=None, description="Test"):
    from finance.services import transactions
    form = {"type": type_, "amount": str(amount), "date": date, "description": description,
            "account_id": str(ids[account])}
    if category:
        form["category_id"] = str(ids[category])
    if to:
        form["to_account_id"] = str(ids[to])
    return transactions.create_transaction(form)
