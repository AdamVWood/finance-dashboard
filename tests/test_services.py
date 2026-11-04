import datetime as dt

import pytest

from finance.services import accounts, budgets, categories, goals, investments, recurring, reports, transactions
from finance.utils import ValidationError

from .conftest import add_txn


# ---------------------------------------------------------------- accounts

def test_balances_follow_transactions(setup):
    add_txn(setup, "income", 500, "2026-02-01", category="salary")
    add_txn(setup, "expense", 120.50, "2026-02-02", category="groceries")
    add_txn(setup, "transfer", 300, "2026-02-03", to="sav")
    add_txn(setup, "expense", 80, "2026-02-04", account="card", category="dining")
    add_txn(setup, "transfer", 150, "2026-02-05", to="card")
    assert accounts.get_account(setup["chq"])["balance_cents"] == 100000 + 50000 - 12050 - 30000 - 15000
    assert accounts.get_account(setup["sav"])["balance_cents"] == 530000
    # Card: owed 200 + 80 spending - 150 payment = 130 owed
    assert accounts.get_account(setup["card"])["balance_cents"] == -13000


def test_liability_opening_balance_is_stored_negative(setup):
    assert accounts.get_account(setup["card"])["opening_balance_cents"] == -20000


def test_account_name_must_be_unique(setup):
    with pytest.raises(ValidationError) as exc:
        accounts.create_account({"name": "chequing", "type": "checking"})
    assert "name" in exc.value.errors


def test_account_with_transactions_cannot_be_deleted(setup):
    add_txn(setup, "expense", 5, "2026-02-01", category="groceries")
    with pytest.raises(ValidationError):
        accounts.delete_account(setup["chq"])


# ---------------------------------------------------------------- transactions

def test_category_must_match_type(setup):
    with pytest.raises(ValidationError) as exc:
        add_txn(setup, "income", 10, "2026-02-01", category="groceries")
    assert "category_id" in exc.value.errors


def test_transfer_needs_different_accounts(setup):
    with pytest.raises(ValidationError) as exc:
        add_txn(setup, "transfer", 10, "2026-02-01", to="chq")
    assert "to_account_id" in exc.value.errors


@pytest.mark.parametrize("amount", ["0", "-5", "abc", "1.001"])
def test_invalid_amounts(setup, amount):
    with pytest.raises(ValidationError) as exc:
        add_txn(setup, "expense", amount, "2026-02-01", category="groceries")
    assert "amount" in exc.value.errors


def test_search_filters_and_totals(setup):
    add_txn(setup, "income", 1000, "2026-02-01", category="salary", description="Pay")
    add_txn(setup, "expense", 40, "2026-02-03", category="groceries", description="Supermarket 50%")
    add_txn(setup, "expense", 15, "2026-03-03", category="dining", description="Lunch")
    f, errors = transactions.parse_filters({"type": "expense"})
    result = transactions.search(f)
    assert not errors and result["count"] == 2 and result["expense_cents"] == 5500 and result["income_cents"] == 0
    f, _ = transactions.parse_filters({"q": "50%"})
    assert transactions.search(f)["count"] == 1  # % is matched literally, not as a wildcard
    f, _ = transactions.parse_filters({"start": "2026-03-01", "end": "2026-03-31"})
    assert transactions.search(f)["count"] == 1
    f, _ = transactions.parse_filters({"min": "20", "max": "100"})
    assert [r["description"] for r in transactions.search(f)["rows"]] == ["Supermarket 50%"]
    f, errors = transactions.parse_filters({"start": "2026-04-01", "end": "2026-03-01"})
    assert errors


def test_csv_round_trip(setup):
    add_txn(setup, "expense", 12.34, "2026-02-01", category="groceries", description="Shop, with comma")
    add_txn(setup, "transfer", 50, "2026-02-02", to="sav", description="Save")
    text = transactions.export_csv({})
    transactions.delete_many([r["id"] for r in transactions.search({})["rows"]])
    assert transactions.import_csv(text) == 2
    rows = transactions.search({"sort": "date_asc"})["rows"]
    assert rows[0]["description"] == "Shop, with comma" and rows[0]["amount_cents"] == 1234
    assert rows[1]["type"] == "transfer" and rows[1]["to_account_id"] == setup["sav"]


def test_csv_import_is_all_or_nothing(setup):
    text = "date,description,amount,category\n2026-02-01,Good,-10,Groceries\nnot-a-date,Bad,-5,Groceries\n"
    with pytest.raises(ValidationError) as exc:
        transactions.import_csv(text, default_account_id=setup["chq"])
    assert any("Row 3" in p for p in exc.value.errors["rows"])
    assert transactions.search({})["count"] == 0


def test_csv_import_uses_sign_and_creates_categories(setup, db):
    text = "date,description,amount,category\n01/02/2026,Coffee,-4.50,Coffee shops\n25/02/2026,Pay,2000,Salary\n"
    assert transactions.import_csv(text, default_account_id=setup["chq"]) == 2
    coffee = categories.find_by_name("Coffee shops", "expense")
    assert coffee is not None
    rows = transactions.search({"sort": "date_asc"})["rows"]
    assert (rows[0]["type"], rows[0]["date"]) == ("expense", "2026-02-01")
    assert rows[1]["type"] == "income"


# ---------------------------------------------------------------- categories

def test_delete_category_in_use_requires_reassignment(setup):
    txn = add_txn(setup, "expense", 10, "2026-02-01", category="dining")
    with pytest.raises(ValidationError):
        categories.delete_category(setup["dining"])
    with pytest.raises(ValidationError):
        categories.delete_category(setup["dining"], reassign_to=setup["salary"])  # wrong kind
    categories.delete_category(setup["dining"], reassign_to=setup["groceries"])
    assert transactions.get_transaction(txn)["category_id"] == setup["groceries"]


# ---------------------------------------------------------------- budgets

def test_budget_counts_only_expenses_in_that_month(setup):
    budgets.set_budget({"category_id": setup["groceries"], "year": "2026", "month": "2", "amount": "100"})
    budgets.set_budget({"category_id": setup["dining"], "year": "2026", "month": "2", "amount": "50"})
    add_txn(setup, "expense", 85, "2026-02-10", category="groceries")
    add_txn(setup, "expense", 60, "2026-02-11", category="dining")
    add_txn(setup, "expense", 999, "2026-03-01", category="groceries")  # other month
    add_txn(setup, "transfer", 500, "2026-02-12", to="sav")              # not spending
    o = budgets.month_overview(2026, 2)
    lines = {line["name"]: line for line in o["lines"]}
    assert lines["Groceries"]["spent_cents"] == 8500 and lines["Groceries"]["status"] == "near"
    assert lines["Dining out"]["status"] == "over"
    assert o["total_budget_cents"] == 15000 and o["spent_budgeted_cents"] == 14500
    assert [line["name"] for line in o["over"]] == ["Dining out"]


def test_unbudgeted_spending_and_copy(setup):
    budgets.set_budget({"category_id": setup["groceries"], "year": "2026", "month": "1", "amount": "100"})
    add_txn(setup, "expense", 30, "2026-02-10", category="dining")
    assert budgets.copy_from_previous(2026, 2) == 1
    o = budgets.month_overview(2026, 2)
    assert o["total_budget_cents"] == 10000 and o["unbudgeted_spent_cents"] == 3000
    budgets.set_budget({"category_id": setup["groceries"], "year": "2026", "month": "2", "amount": ""})
    assert not budgets.month_overview(2026, 2)["has_budgets"]


def test_budget_only_for_expense_categories(setup):
    with pytest.raises(ValidationError):
        budgets.set_budget({"category_id": setup["salary"], "year": "2026", "month": "2", "amount": "1"})


# ---------------------------------------------------------------- goals

def test_goal_progress_and_required_monthly(app, monkeypatch):
    import finance.services.goals as g
    monkeypatch.setattr(g, "today", lambda: dt.date(2026, 7, 1))
    gid = goals.create_goal({"name": "Laptop", "target": "1200", "start_date": "2026-01-01",
                             "deadline": "2027-01-01", "initial": "600"})
    goal = goals.get_goal(gid)
    assert goal["progress_pct"] == 50 and goal["remaining_cents"] == 60000
    assert goal["months_left"] == 6 and goal["required_monthly_cents"] == 10000
    assert goal["status"] == "on_track"
    goals.add_contribution(gid, {"amount": "100", "direction": "withdraw", "date": "2026-06-30"})
    assert goals.get_goal(gid)["status"] == "behind"
    with pytest.raises(ValidationError):
        goals.add_contribution(gid, {"amount": "5000", "direction": "withdraw"})


def test_goal_completed_and_deadline_validation(app):
    gid = goals.create_goal({"name": "Small", "target": "10", "initial": "10"})
    assert goals.get_goal(gid)["status"] == "done"
    with pytest.raises(ValidationError):
        goals.create_goal({"name": "Bad", "target": "10", "start_date": "2026-05-01", "deadline": "2026-04-01"})


# ---------------------------------------------------------------- investments

def test_portfolio_value_and_return(app):
    investments.create_holding({"name": "ETF", "asset_type": "etf", "quantity": "10", "purchase_price": "100",
                                "purchase_date": "2026-01-05", "current_price": "115"})
    investments.create_holding({"name": "Coin", "asset_type": "crypto", "quantity": "0.5", "purchase_price": "1000",
                                "purchase_date": "2026-01-05"})
    s = investments.portfolio_summary()
    assert s["cost_cents"] == 150000 and s["value_cents"] == 165000 and s["gain_cents"] == 15000
    assert round(s["return_pct"], 2) == 10.0 and s["stale_count"] == 1
    assert {a["label"] for a in s["allocation"]} == {"ETF", "Crypto"}


def test_funding_and_selling_move_cash(setup):
    hid = investments.create_holding({"name": "ETF", "asset_type": "etf", "quantity": "10", "purchase_price": "100",
                                      "purchase_date": "2026-02-01", "funding_account_id": str(setup["sav"])})
    assert accounts.get_account(setup["sav"])["balance_cents"] == 500000 - 100000
    before = reports.net_worth(dt.date(2026, 3, 1))["net_worth_cents"]
    investments.sell_holding(hid, {"sale_price": "130", "sold_on": "2026-03-15",
                                   "proceeds_account_id": str(setup["chq"])})
    assert accounts.get_account(setup["chq"])["balance_cents"] == 100000 + 130000
    assert investments.value_at("2026-03-20") == 0 and investments.value_at("2026-03-01") == 100000
    assert investments.realised_summary()["gain_cents"] == 30000
    after = reports.net_worth(dt.date(2026, 3, 20))["net_worth_cents"]
    assert after - before == 30000  # only the gain changes net worth
    investments.undo_sale(hid)
    assert investments.portfolio_summary()["count"] == 1


def test_price_updates_build_history(app):
    hid = investments.create_holding({"name": "X", "asset_type": "stock", "quantity": "2", "purchase_price": "10",
                                      "purchase_date": "2026-01-01"})
    investments.update_prices({hid: "12"}, "2026-02-01")
    investments.update_prices({hid: "15"}, "2026-03-01")
    assert [p["price"] for p in investments.price_history(hid)] == [10, 12, 15]
    assert investments.value_at("2026-02-15") == 2400
    with pytest.raises(ValidationError):
        investments.update_prices({hid: "abc"})


# ---------------------------------------------------------------- recurring

def test_monthly_schedule_keeps_anchor_day():
    start = dt.date(2026, 1, 31)
    assert recurring.next_after(start, "monthly", start) == dt.date(2026, 2, 28)
    assert recurring.next_after(start, "monthly", dt.date(2026, 2, 28)) == dt.date(2026, 3, 31)
    assert recurring.next_after(dt.date(2026, 1, 1), "biweekly", dt.date(2026, 1, 1)) == dt.date(2026, 1, 15)
    assert recurring.next_after(dt.date(2026, 1, 1), "yearly", dt.date(2026, 6, 1)) == dt.date(2027, 1, 1)


def test_post_due_creates_transactions_and_advances(setup):
    rid = recurring.create_item({"type": "expense", "amount": "50", "description": "Phone",
                                 "account_id": str(setup["chq"]), "category_id": str(setup["dining"]),
                                 "frequency": "monthly", "start_date": "2026-01-15", "end_date": "2026-03-31"})
    assert len(recurring.due_occurrences(dt.date(2026, 4, 30))) == 3
    assert recurring.post_due(ref=dt.date(2026, 2, 20)) == 2
    assert recurring.get_item(rid)["next_date"] == "2026-03-15"
    assert recurring.post_due(ref=dt.date(2026, 2, 20)) == 0  # nothing posted twice
    assert recurring.post_due(ref=dt.date(2026, 12, 1)) == 1  # end date respected
    assert transactions.search({})["count"] == 3


# ---------------------------------------------------------------- reports

def test_income_expense_and_savings_rate(setup):
    add_txn(setup, "income", 2000, "2026-02-01", category="salary")
    add_txn(setup, "expense", 500, "2026-02-03", category="groceries")
    add_txn(setup, "transfer", 700, "2026-02-04", to="sav")
    r = reports.income_expense(dt.date(2026, 2, 1), dt.date(2026, 2, 28))
    assert r["income_cents"] == 200000 and r["expense_cents"] == 50000 and r["savings_rate"] == 75
    series = reports.monthly_series(3, end=dt.date(2026, 3, 15))
    assert [m["income_cents"] for m in series] == [0, 200000, 0]


def test_net_worth_history_respects_opening_dates(setup, db):
    worth = reports.net_worth(dt.date(2026, 2, 1))
    assert worth["cash_assets_cents"] == 600000 and worth["liabilities_cents"] == 20000
    assert worth["net_worth_cents"] == 580000
    assert reports.net_worth(dt.date(2025, 12, 31))["net_worth_cents"] == 0
    history = reports.net_worth_history(3, ref=dt.date(2026, 2, 15))
    assert [p["net_worth_cents"] for p in history] == [0, 580000, 580000]
