"""Investment holdings, price updates and portfolio statistics.

Live market prices need an external data provider (and usually an API key),
so prices are entered manually. Every price update is kept in
``investment_prices`` which lets the app chart portfolio value over time.
"""

from ..db import get_db
from ..utils import ValidationError, Validator, to_cents, today
from . import accounts as accounts_svc

ASSET_TYPES = {
    "stock": "Stock",
    "etf": "ETF",
    "mutual_fund": "Mutual fund",
    "bond": "Bond",
    "crypto": "Crypto",
    "real_estate": "Real estate",
    "cash_equivalent": "Cash equivalent / fixed deposit",
    "other": "Other",
}


def _enrich(h):
    h["type_label"] = ASSET_TYPES.get(h["asset_type"], h["asset_type"])
    h["is_sold"] = bool(h["sold_on"])
    if h["is_sold"]:
        price = h["sale_price"]
    else:
        price = h["current_price"] if h["current_price"] is not None else h["purchase_price"]
    h["effective_price"] = price
    h["cost_cents"] = to_cents(h["quantity"] * h["purchase_price"])
    h["value_cents"] = to_cents(h["quantity"] * price)
    h["gain_cents"] = h["value_cents"] - h["cost_cents"]
    h["return_pct"] = (h["gain_cents"] / h["cost_cents"] * 100) if h["cost_cents"] else None
    h["price_is_stale"] = h["current_price"] is None and not h["is_sold"]
    return h


HOLDING_SQL = """
    SELECT i.*, fa.name AS funding_account_name, pa.name AS proceeds_account_name
    FROM investments i
    LEFT JOIN accounts fa ON fa.id = i.funding_account_id
    LEFT JOIN accounts pa ON pa.id = i.proceeds_account_id
"""


def list_holdings(sort="value", sold=False):
    where = " WHERE i.sold_on IS NOT NULL" if sold else " WHERE i.sold_on IS NULL"
    rows = [_enrich(dict(r)) for r in get_db().execute(HOLDING_SQL + where)]
    keys = {
        "value": lambda h: -h["value_cents"],
        "name": lambda h: h["name"].lower(),
        "return": lambda h: -(h["return_pct"] or 0),
        "date": lambda h: h["purchase_date"],
        "type": lambda h: (h["type_label"], -h["value_cents"]),
    }
    return sorted(rows, key=keys.get(sort, keys["value"]))


def get_holding(holding_id):
    row = get_db().execute(HOLDING_SQL + " WHERE i.id = ?", (holding_id,)).fetchone()
    return _enrich(dict(row)) if row else None


def portfolio_summary(holdings=None):
    holdings = list_holdings() if holdings is None else holdings
    cost = sum(h["cost_cents"] for h in holdings)
    value = sum(h["value_cents"] for h in holdings)
    allocation = {}
    for h in holdings:
        allocation[h["type_label"]] = allocation.get(h["type_label"], 0) + h["value_cents"]
    allocation = sorted(
        ({"label": k, "value_cents": v, "pct": (v / value * 100) if value else 0} for k, v in allocation.items()),
        key=lambda a: -a["value_cents"],
    )
    priced = [h for h in holdings if h["return_pct"] is not None]
    best = max(priced, key=lambda h: h["return_pct"], default=None)
    worst = min(priced, key=lambda h: h["return_pct"], default=None)
    return {
        "count": len(holdings),
        "cost_cents": cost,
        "value_cents": value,
        "gain_cents": value - cost,
        "return_pct": ((value - cost) / cost * 100) if cost else None,
        "allocation": allocation,
        "best": best,
        "worst": worst if worst is not best else None,
        "stale_count": sum(1 for h in holdings if h["price_is_stale"]),
    }


def realised_summary(sold=None):
    sold = list_holdings("date", sold=True) if sold is None else sold
    cost = sum(h["cost_cents"] for h in sold)
    proceeds = sum(h["value_cents"] for h in sold)
    return {"count": len(sold), "cost_cents": cost, "proceeds_cents": proceeds, "gain_cents": proceeds - cost}


def value_at(date_iso):
    """Portfolio market value on a given date, using the latest known price."""
    rows = get_db().execute(
        """SELECT i.quantity,
                  COALESCE((SELECT p.price FROM investment_prices p
                            WHERE p.investment_id = i.id AND p.date <= :d
                            ORDER BY p.date DESC LIMIT 1), i.purchase_price) AS price
           FROM investments i
           WHERE i.purchase_date <= :d AND (i.sold_on IS NULL OR i.sold_on > :d)""",
        {"d": date_iso},
    )
    return sum(to_cents(r["quantity"] * r["price"]) for r in rows)


def _validate(form):
    v = Validator(form)
    name = v.text("name", "Name", max_length=100)
    ticker = (v.text("ticker", "Ticker / symbol", required=False, max_length=20) or "").upper() or None
    asset_type = v.choice("asset_type", "Asset type", ASSET_TYPES)
    quantity = v.number("quantity", "Quantity", positive=True)
    purchase_price = v.number("purchase_price", "Purchase price per unit", minimum=0)
    purchase_date = v.date("purchase_date", "Purchase date")
    current_price = v.number("current_price", "Current price per unit", required=False, minimum=0)
    notes = v.text("notes", "Notes", required=False, max_length=500)
    funding = v.integer("funding_account_id", "Paid from", required=False)
    if purchase_date and purchase_date > today().isoformat():
        v.error("purchase_date", "Purchase date can't be in the future.")
    if funding:
        acc = accounts_svc.get_account(funding)
        if not acc:
            v.error("funding_account_id", "Choose a valid account.")
        elif purchase_date and acc["opened_on"] > purchase_date:
            v.error("funding_account_id", "That account didn't exist yet on the purchase date.")
    v.raise_if_errors()
    return {
        "name": name,
        "ticker": ticker,
        "asset_type": asset_type,
        "quantity": quantity,
        "purchase_price": purchase_price,
        "purchase_date": purchase_date,
        "current_price": current_price,
        "notes": notes,
        "funding_account_id": funding,
    }


def _record_price(db, holding_id, price, date_iso):
    db.execute(
        """INSERT INTO investment_prices (investment_id, date, price) VALUES (?, ?, ?)
           ON CONFLICT (investment_id, date) DO UPDATE SET price = excluded.price""",
        (holding_id, date_iso, price),
    )


def create_holding(form):
    data = _validate(form)
    data["price_date"] = today().isoformat() if data["current_price"] is not None else None
    db = get_db()
    holding_id = db.execute(
        """INSERT INTO investments (name, ticker, asset_type, quantity, purchase_price, purchase_date,
                                    current_price, price_date, notes, funding_account_id)
           VALUES (:name, :ticker, :asset_type, :quantity, :purchase_price, :purchase_date,
                   :current_price, :price_date, :notes, :funding_account_id)""",
        data,
    ).lastrowid
    _record_price(db, holding_id, data["purchase_price"], data["purchase_date"])
    if data["current_price"] is not None:
        _record_price(db, holding_id, data["current_price"], data["price_date"])
    db.commit()
    return holding_id


def to_form(h):
    def num(x):
        return "" if x is None else f"{x:.10g}"

    return {
        "name": h["name"],
        "ticker": h["ticker"] or "",
        "asset_type": h["asset_type"],
        "quantity": num(h["quantity"]),
        "purchase_price": num(h["purchase_price"]),
        "purchase_date": h["purchase_date"],
        "current_price": num(h["current_price"]),
        "notes": h["notes"] or "",
        "funding_account_id": str(h["funding_account_id"] or ""),
    }


def update_holding(holding_id, form):
    existing = get_holding(holding_id)
    if not existing:
        raise ValidationError("Investment not found.")
    data = _validate(form)
    data["id"] = holding_id
    price_changed = data["current_price"] is not None and data["current_price"] != existing["current_price"]
    data["price_date"] = today().isoformat() if price_changed else existing["price_date"]
    if data["current_price"] is None:
        data["price_date"] = None
    db = get_db()
    db.execute(
        """UPDATE investments SET name=:name, ticker=:ticker, asset_type=:asset_type, quantity=:quantity,
               purchase_price=:purchase_price, purchase_date=:purchase_date, current_price=:current_price,
               price_date=:price_date, notes=:notes, funding_account_id=:funding_account_id WHERE id=:id""",
        data,
    )
    # Keep the purchase-date price point in step with the edited purchase details.
    db.execute(
        "DELETE FROM investment_prices WHERE investment_id = ? AND date < ?", (holding_id, data["purchase_date"])
    )
    _record_price(db, holding_id, data["purchase_price"], data["purchase_date"])
    if price_changed:
        _record_price(db, holding_id, data["current_price"], data["price_date"])
    db.commit()


def update_prices(prices, date_iso=None):
    """Bulk price update. ``prices`` maps holding id -> raw price input."""
    date_iso = date_iso or today().isoformat()
    errors, updated = {}, 0
    db = get_db()
    for holding_id, raw in prices.items():
        raw = (raw or "").strip()
        if not raw:
            continue
        v = Validator({"p": raw})
        price = v.number("p", "Price", minimum=0)
        if v.errors:
            errors[f"price_{holding_id}"] = v.errors["p"]
            continue
        cur = db.execute(
            "UPDATE investments SET current_price = ?, price_date = ? WHERE id = ? AND sold_on IS NULL",
            (price, date_iso, holding_id)
        )
        if cur.rowcount:
            _record_price(db, holding_id, price, date_iso)
            updated += 1
    if errors:
        db.rollback()
        raise ValidationError(errors)
    db.commit()
    return updated


def sell_holding(holding_id, form):
    """Mark a holding as sold. The proceeds can be paid into one of your accounts."""
    h = get_holding(holding_id)
    if not h:
        raise ValidationError("Investment not found.")
    if h["is_sold"]:
        raise ValidationError("This holding has already been sold.")
    v = Validator(form)
    price = v.number("sale_price", "Sale price per unit", minimum=0)
    sold_on = v.date("sold_on", "Sale date")
    proceeds = v.integer("proceeds_account_id", "Paid into", required=False)
    if sold_on and sold_on < h["purchase_date"]:
        v.error("sold_on", "The sale date can't be before the purchase date.")
    if sold_on and sold_on > today().isoformat():
        v.error("sold_on", "The sale date can't be in the future.")
    if proceeds and not accounts_svc.get_account(proceeds):
        v.error("proceeds_account_id", "Choose a valid account.")
    v.raise_if_errors()
    db = get_db()
    db.execute("UPDATE investments SET sold_on = ?, sale_price = ?, proceeds_account_id = ? WHERE id = ?",
               (sold_on, price, proceeds, holding_id))
    _record_price(db, holding_id, price, sold_on)
    db.commit()


def undo_sale(holding_id):
    db = get_db()
    if db.execute("UPDATE investments SET sold_on = NULL, sale_price = NULL, proceeds_account_id = NULL "
                  "WHERE id = ? AND sold_on IS NOT NULL", (holding_id,)).rowcount == 0:
        raise ValidationError("That holding isn't marked as sold.")
    db.commit()


def delete_holding(holding_id):
    db = get_db()
    if db.execute("DELETE FROM investments WHERE id = ?", (holding_id,)).rowcount == 0:
        raise ValidationError("Investment not found.")
    db.commit()


def price_history(holding_id):
    return [
        dict(r)
        for r in get_db().execute(
            "SELECT date, price FROM investment_prices WHERE investment_id = ? ORDER BY date", (holding_id,)
        )
    ]
