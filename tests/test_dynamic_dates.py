"""The app must follow the real calendar: nothing about the current month is hard-coded."""
import datetime as dt
import types

import pytest

import finance.utils as utils


class FakeDate(dt.date):
    fixed = None

    @classmethod
    def today(cls):
        return cls.fixed


@pytest.fixture
def on_date(monkeypatch):
    def set_date(year, month, day):
        FakeDate.fixed = FakeDate(year, month, day)
        monkeypatch.setattr(utils, "dt", types.SimpleNamespace(date=FakeDate, datetime=dt.datetime,
                                                               timedelta=dt.timedelta))
    return set_date


@pytest.mark.parametrize("year,month,day,month_name", [
    (2027, 2, 15, "February"), (2027, 3, 1, "March"), (2028, 12, 31, "December"),
])
def test_pages_follow_the_current_date(client, on_date, year, month, day, month_name):
    on_date(year, month, day)
    dashboard = client.get("/").get_data(as_text=True)
    assert f"Budget · {month_name}" in dashboard
    assert f"1 {month_name[:3]} – " in dashboard          # "This month · 1 Feb – 28 Feb 2027"
    budgets = client.get("/budgets/").get_data(as_text=True)
    assert f"{month_name} {year}" in budgets
    reports = client.get("/reports/").get_data(as_text=True)
    assert f"Income {year}" in reports
    form = client.get("/transactions/new").get_data(as_text=True)
    assert f'value="{year}-{month:02d}-{day:02d}"' in form or "Add an account first" in form


def test_period_rolls_over_at_month_end(on_date):
    on_date(2027, 1, 31)
    assert utils.period_range("this_month") == (dt.date(2027, 1, 1), dt.date(2027, 1, 31))
    on_date(2027, 2, 1)
    assert utils.period_range("this_month") == (dt.date(2027, 2, 1), dt.date(2027, 2, 28))
    assert utils.period_range("last_month") == (dt.date(2027, 1, 1), dt.date(2027, 1, 31))
