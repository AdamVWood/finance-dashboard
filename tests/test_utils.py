import datetime as dt

import pytest

from finance.utils import add_months, cents_to_input, format_money, parse_money, period_range


@pytest.mark.parametrize("raw,cents", [
    ("12", 1200), ("12.5", 1250), ("1,234.56", 123456), ("$9.99", 999), ("-4.10", -410), ("(3.00)", -300),
    (" 0.01 ", 1),
])
def test_parse_money(raw, cents):
    assert parse_money(raw) == cents


@pytest.mark.parametrize("raw", ["abc", "1.234", "", "nan", "inf", "1e30"])
def test_parse_money_rejects(raw):
    with pytest.raises(ValueError):
        parse_money(raw)


def test_money_formatting():
    assert format_money(123456) == "$1,234.56"
    assert format_money(-5) == "−$0.05"
    assert format_money(1500, show_sign=True) == "+$15.00"
    assert format_money(123456, decimals=False) == "$1,235"
    assert cents_to_input(-1005) == "-10.05"


def test_add_months_clamps_month_end():
    assert add_months(dt.date(2026, 1, 31), 1) == dt.date(2026, 2, 28)
    assert add_months(dt.date(2024, 1, 31), 1) == dt.date(2024, 2, 29)
    assert add_months(dt.date(2026, 11, 15), 3) == dt.date(2027, 2, 15)
    assert add_months(dt.date(2026, 1, 15), -1) == dt.date(2025, 12, 15)


def test_period_ranges():
    ref = dt.date(2026, 3, 10)
    assert period_range("this_month", ref) == (dt.date(2026, 3, 1), dt.date(2026, 3, 31))
    assert period_range("last_month", ref) == (dt.date(2026, 2, 1), dt.date(2026, 2, 28))
    assert period_range("last_3_months", ref) == (dt.date(2026, 1, 1), dt.date(2026, 3, 31))
    assert period_range("last_12_months", ref)[0] == dt.date(2025, 4, 1)
    assert period_range("bogus", ref) == (None, None)
