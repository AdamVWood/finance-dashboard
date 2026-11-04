"""Shared helpers: money handling, date maths and form validation."""

import calendar
import datetime as dt
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

MAX_CENTS = 100_000_000_000_00  # 100 billion - a sanity limit for one amount


class ValidationError(Exception):
    """Raised by services when submitted data is invalid.

    ``errors`` maps a form field name to a human-readable message. The key
    ``"_form"`` is used for errors that are not tied to a single field.
    """

    def __init__(self, errors):
        if isinstance(errors, str):
            errors = {"_form": errors}
        self.errors = errors
        super().__init__("; ".join(f"{k}: {v}" for k, v in errors.items()))


class Validator:
    """Collects cleaned values and errors while reading a submitted form.

    Usage::

        v = Validator(form)
        amount = v.money("amount")
        when = v.date("date")
        v.raise_if_errors()
    """

    def __init__(self, data):
        self.data = data or {}
        self.errors = {}

    def raw(self, field):
        value = self.data.get(field)
        return value.strip() if isinstance(value, str) else value

    def error(self, field, message):
        self.errors.setdefault(field, message)

    def text(self, field, label, required=True, max_length=200):
        value = self.raw(field) or ""
        if required and not value:
            self.error(field, f"{label} is required.")
        elif len(value) > max_length:
            self.error(field, f"{label} must be {max_length} characters or fewer.")
        return value or None

    def choice(self, field, label, choices, required=True):
        value = self.raw(field) or ""
        if not value:
            if required:
                self.error(field, f"Please choose a {label.lower()}.")
            return None
        if value not in choices:
            self.error(field, f"Invalid {label.lower()}.")
            return None
        return value

    def money(self, field, label="Amount", required=True, allow_zero=False, allow_negative=False):
        value = self.raw(field) or ""
        if not value:
            if required:
                self.error(field, f"{label} is required.")
            return None
        try:
            cents = parse_money(value)
        except ValueError as exc:
            self.error(field, f"{label}: {exc}")
            return None
        if cents < 0 and not allow_negative:
            self.error(field, f"{label} cannot be negative.")
        elif cents == 0 and not allow_zero:
            self.error(field, f"{label} must be greater than zero.")
        return cents

    def number(self, field, label, required=True, minimum=None, positive=False):
        value = self.raw(field) or ""
        if not value:
            if required:
                self.error(field, f"{label} is required.")
            return None
        try:
            number = float(Decimal(value.replace(",", "")))
        except (InvalidOperation, ValueError):
            self.error(field, f"{label} must be a number.")
            return None
        if number != number or number in (float("inf"), float("-inf")):
            self.error(field, f"{label} must be a number.")
            return None
        if positive and number <= 0:
            self.error(field, f"{label} must be greater than zero.")
        elif minimum is not None and number < minimum:
            self.error(field, f"{label} must be at least {minimum}.")
        return number

    def integer(self, field, label, required=True, minimum=None, maximum=None):
        value = self.raw(field) or ""
        if not value:
            if required:
                self.error(field, f"{label} is required.")
            return None
        try:
            number = int(value)
        except ValueError:
            self.error(field, f"{label} must be a whole number.")
            return None
        if (minimum is not None and number < minimum) or (maximum is not None and number > maximum):
            self.error(field, f"{label} must be between {minimum} and {maximum}.")
        return number

    def date(self, field, label="Date", required=True):
        value = self.raw(field) or ""
        if not value:
            if required:
                self.error(field, f"{label} is required.")
            return None
        try:
            parsed = parse_date(value)
        except ValueError:
            self.error(field, f"{label} must be a valid date (YYYY-MM-DD).")
            return None
        if not (1990 <= parsed.year <= 2100):
            self.error(field, f"{label} must be between 1990 and 2100.")
        return parsed.isoformat()

    def flag(self, field):
        return 1 if self.raw(field) in ("1", "on", "true", "yes", True) else 0

    def raise_if_errors(self):
        if self.errors:
            raise ValidationError(self.errors)


# ---------------------------------------------------------------------------
# Money
# ---------------------------------------------------------------------------

def parse_money(value):
    """Convert user input such as '1,234.50' or '$12' into integer cents."""
    if isinstance(value, int):
        return value * 100
    text = str(value).strip().replace(",", "").replace("$", "").replace(" ", "")
    negative = False
    if text.startswith("(") and text.endswith(")"):
        negative, text = True, text[1:-1]
    if text.startswith("-"):
        negative, text = not negative, text[1:]
    if not text:
        raise ValueError("enter an amount")
    try:
        amount = Decimal(text)
    except InvalidOperation:
        raise ValueError("enter a valid number, e.g. 1250.00") from None
    if not amount.is_finite():
        raise ValueError("enter a valid number")
    if amount.as_tuple().exponent < -2:
        raise ValueError("use at most two decimal places")
    cents = int((amount * 100).to_integral_value(rounding=ROUND_HALF_UP))
    if cents > MAX_CENTS:
        raise ValueError("amount is too large")
    return -cents if negative else cents


def to_cents(value):
    """Round a float currency amount to integer cents."""
    return int(Decimal(str(value)).scaleb(2).to_integral_value(rounding=ROUND_HALF_UP))


def cents_to_input(cents):
    """Format cents for an <input> value (no symbol or thousands separator)."""
    if cents is None:
        return ""
    sign = "-" if cents < 0 else ""
    cents = abs(int(cents))
    return f"{sign}{cents // 100}.{cents % 100:02d}"


def format_money(cents, symbol="$", show_sign=False, decimals=True):
    if cents is None:
        return "—"
    cents = int(round(cents))
    sign = ""
    if cents < 0:
        sign = "−"
    elif show_sign and cents > 0:
        sign = "+"
    cents = abs(cents)
    if decimals:
        body = f"{cents // 100:,}.{cents % 100:02d}"
    else:
        body = f"{int(Decimal(cents).scaleb(-2).to_integral_value(rounding=ROUND_HALF_UP)):,}"
    return f"{sign}{symbol}{body}"


def pct(part, whole):
    """Percentage as a float, or None when the whole is zero."""
    if not whole:
        return None
    return part / whole * 100


# ---------------------------------------------------------------------------
# Dates
# ---------------------------------------------------------------------------

def today():
    return dt.date.today()


def parse_date(value):
    if isinstance(value, dt.date):
        return value
    text = str(value).strip()
    for fmt in ("%Y-%m-%d", "%d/%m/%Y", "%m/%d/%Y", "%Y/%m/%d", "%d-%m-%Y"):
        try:
            return dt.datetime.strptime(text, fmt).date()
        except ValueError:
            continue
    raise ValueError(f"Unrecognised date: {value!r}")


def month_start(day):
    return day.replace(day=1)


def month_end(day):
    return day.replace(day=calendar.monthrange(day.year, day.month)[1])


def add_months(day, months):
    month_index = day.month - 1 + months
    year = day.year + month_index // 12
    month = month_index % 12 + 1
    return dt.date(year, month, min(day.day, calendar.monthrange(year, month)[1]))


def month_label(year, month, short=True):
    name = calendar.month_abbr[month] if short else calendar.month_name[month]
    return f"{name} {year}"


def last_n_months(n, end=None):
    """List of (year, month) tuples for the last n months, oldest first."""
    end = end or today()
    first = add_months(month_start(end), -(n - 1))
    return [(add_months(first, i).year, add_months(first, i).month) for i in range(n)]


PERIODS = {
    "this_month": "This month",
    "last_month": "Last month",
    "last_3_months": "Last 3 months",
    "this_year": "This year",
    "last_12_months": "Last 12 months",
    "last_year": "Last year",
    "all_time": "All time",
}


def period_range(option, ref=None):
    """Return (start, end) dates for a named period, or (None, None)."""
    ref = ref or today()
    if option == "this_month":
        return month_start(ref), month_end(ref)
    if option == "last_month":
        prev = add_months(month_start(ref), -1)
        return prev, month_end(prev)
    if option == "last_3_months":
        return add_months(month_start(ref), -2), month_end(ref)
    if option == "this_year":
        return dt.date(ref.year, 1, 1), dt.date(ref.year, 12, 31)
    if option == "last_12_months":
        return add_months(month_start(ref), -11), month_end(ref)
    if option == "last_year":
        return dt.date(ref.year - 1, 1, 1), dt.date(ref.year - 1, 12, 31)
    if option == "all_time":
        return dt.date(1990, 1, 1), dt.date(2100, 12, 31)
    return None, None


def previous_period(option, ref=None):
    """The comparable period immediately before ``option`` (for deltas)."""
    ref = ref or today()
    if option == "this_month":
        return period_range("last_month", ref)
    if option == "last_month":
        return period_range("last_month", add_months(ref, -1))
    if option == "this_year":
        return period_range("last_year", ref)
    if option == "last_year":
        return period_range("last_year", dt.date(ref.year - 1, 6, 1))
    if option == "last_3_months":
        start, _ = period_range("last_3_months", ref)
        return add_months(start, -3), month_end(add_months(start, -1))
    if option == "last_12_months":
        start, _ = period_range("last_12_months", ref)
        return add_months(start, -12), month_end(add_months(start, -1))
    return None, None
