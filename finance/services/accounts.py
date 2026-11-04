"""Bank accounts, cash, credit cards and loans.

Balances are never stored; they are always derived from the opening balance
plus the transactions recorded against the account, so they can't drift out
of sync. Liability balances are negative (an amount owed).
"""

from ..db import get_db
from ..utils import ValidationError, Validator, today

ACCOUNT_TYPES = {
    "checking": "Chequing / current",
    "savings": "Savings",
    "cash": "Cash",
    "other_asset": "Other asset",
    "credit_card": "Credit card",
    "loan": "Loan / mortgage",
    "other_liability": "Other liability",
}
LIABILITY_TYPES = {"credit_card", "loan", "other_liability"}


def is_liability(account_type):
    return account_type in LIABILITY_TYPES


# Balance on :as_of = opening balance (from its date) + income - expenses +/- transfers
# - investments bought with this account + proceeds of investments sold into it.
BALANCE_SQL = """
    (CASE WHEN a.opened_on <= :as_of THEN a.opening_balance_cents ELSE 0 END)
    - COALESCE((SELECT SUM(CAST(ROUND(i.quantity * i.purchase_price * 100) AS INTEGER)) FROM investments i
                WHERE i.funding_account_id = a.id AND i.purchase_date <= :as_of), 0)
    + COALESCE((SELECT SUM(CAST(ROUND(i.quantity * i.sale_price * 100) AS INTEGER)) FROM investments i
                WHERE i.proceeds_account_id = a.id AND i.sold_on <= :as_of), 0)
    + COALESCE((SELECT SUM(CASE WHEN t.type = 'income' THEN t.amount_cents ELSE -t.amount_cents END)
                FROM transactions t WHERE t.account_id = a.id AND t.date <= :as_of), 0)
    + COALESCE((SELECT SUM(t.amount_cents) FROM transactions t
                WHERE t.to_account_id = a.id AND t.date <= :as_of), 0)
"""


def list_accounts(include_archived=False, as_of=None):
    as_of = as_of or "9999-12-31"
    sql = f"""
        SELECT a.*, ({BALANCE_SQL}) AS balance_cents,
               (SELECT COUNT(*) FROM transactions t
                WHERE t.account_id = a.id OR t.to_account_id = a.id) AS txn_count
        FROM accounts a
        WHERE (:all = 1 OR a.is_archived = 0)
        ORDER BY a.is_archived, CASE WHEN a.type IN ('credit_card','loan','other_liability') THEN 1 ELSE 0 END,
                 a.name COLLATE NOCASE"""
    rows = get_db().execute(sql, {"as_of": as_of, "all": 1 if include_archived else 0})
    accounts = []
    for row in rows:
        acc = dict(row)
        acc["is_liability"] = is_liability(acc["type"])
        acc["type_label"] = ACCOUNT_TYPES.get(acc["type"], acc["type"])
        accounts.append(acc)
    return accounts


def get_account(account_id):
    row = get_db().execute(
        f"SELECT a.*, ({BALANCE_SQL}) AS balance_cents FROM accounts a WHERE a.id = :id",
        {"id": account_id, "as_of": "9999-12-31"},
    ).fetchone()
    if not row:
        return None
    acc = dict(row)
    acc["is_liability"] = is_liability(acc["type"])
    acc["type_label"] = ACCOUNT_TYPES.get(acc["type"], acc["type"])
    return acc


def find_by_name(name):
    row = get_db().execute("SELECT * FROM accounts WHERE name = ? COLLATE NOCASE", (name.strip(),)).fetchone()
    return dict(row) if row else None


def totals(as_of=None):
    """Sum of asset and liability account balances (liabilities as positive owed)."""
    assets = liabilities = 0
    for acc in list_accounts(include_archived=True, as_of=as_of):
        if acc["is_liability"]:
            liabilities += -acc["balance_cents"]
        else:
            assets += acc["balance_cents"]
    return {"cash_assets_cents": assets, "liabilities_cents": liabilities}


def _validate(form, account_id=None):
    v = Validator(form)
    name = v.text("name", "Name", max_length=60)
    account_type = v.choice("type", "Account type", ACCOUNT_TYPES)
    institution = v.text("institution", "Institution", required=False, max_length=80)
    opening = v.money("opening_balance", "Opening balance", required=False, allow_zero=True, allow_negative=True)
    opened_on = v.date("opened_on", "Opening date", required=False) or today().isoformat()
    notes = v.text("notes", "Notes", required=False, max_length=500)
    if name:
        clash = get_db().execute(
            "SELECT id FROM accounts WHERE name = ? COLLATE NOCASE AND id IS NOT ?", (name, account_id)
        ).fetchone()
        if clash:
            v.error("name", f"An account called '{name}' already exists.")
    if account_id:
        first = get_db().execute(
            "SELECT MIN(date) FROM transactions WHERE account_id = ? OR to_account_id = ?", (account_id, account_id)
        ).fetchone()[0]
        if first and opened_on > first:
            v.error("opened_on", f"Opening date can't be after the account's first transaction ({first}).")
    v.raise_if_errors()
    opening = opening or 0
    # For liabilities the form asks "amount owed" as a positive number.
    if is_liability(account_type):
        opening = -abs(opening)
    return {
        "name": name,
        "type": account_type,
        "institution": institution,
        "opening_balance_cents": opening,
        "opened_on": opened_on,
        "notes": notes,
        "is_archived": v.flag("is_archived"),
    }


def create_account(form):
    data = _validate(form)
    db = get_db()
    cur = db.execute(
        """INSERT INTO accounts (name, type, institution, opening_balance_cents, opened_on, notes, is_archived)
           VALUES (:name, :type, :institution, :opening_balance_cents, :opened_on, :notes, :is_archived)""",
        data,
    )
    db.commit()
    return cur.lastrowid


def update_account(account_id, form):
    if not get_account(account_id):
        raise ValidationError("Account not found.")
    data = _validate(form, account_id)
    data["id"] = account_id
    db = get_db()
    db.execute(
        """UPDATE accounts SET name=:name, type=:type, institution=:institution,
               opening_balance_cents=:opening_balance_cents, opened_on=:opened_on,
               notes=:notes, is_archived=:is_archived
           WHERE id=:id""",
        data,
    )
    db.commit()


def delete_account(account_id):
    db = get_db()
    if not get_account(account_id):
        raise ValidationError("Account not found.")
    used = db.execute(
        "SELECT COUNT(*) FROM transactions WHERE account_id = ? OR to_account_id = ?", (account_id, account_id)
    ).fetchone()[0]
    used += db.execute(
        "SELECT COUNT(*) FROM investments WHERE funding_account_id = ? OR proceeds_account_id = ?",
        (account_id, account_id),
    ).fetchone()[0]
    used += db.execute("SELECT COUNT(*) FROM recurring WHERE account_id = ? OR to_account_id = ?",
                       (account_id, account_id)).fetchone()[0]
    if used:
        raise ValidationError(
            "This account is used by transactions, recurring items or investments. Archive it instead."
        )
    db.execute("DELETE FROM accounts WHERE id = ?", (account_id,))
    db.commit()
