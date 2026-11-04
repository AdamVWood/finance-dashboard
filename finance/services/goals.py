"""Savings goals and the contributions made towards them.

A goal's progress is the sum of its contributions (withdrawals are negative
contributions), so the full history is kept and can be charted.
"""

import datetime as dt

from ..db import get_db
from ..utils import ValidationError, Validator, add_months, cents_to_input, parse_date, today

ON_TRACK_TOLERANCE = 5  # percentage points behind the straight-line plan still counted as on track


def _months_between(start, end):
    days = (end - start).days
    return days / 30.4375


def _enrich(goal, ref=None):
    ref = ref or today()
    target = goal["target_cents"]
    saved = goal["saved_cents"] or 0
    goal["saved_cents"] = saved
    goal["remaining_cents"] = max(0, target - saved)
    goal["progress_pct"] = min(100.0, max(0.0, saved / target * 100)) if target else 0
    goal["required_monthly_cents"] = None
    goal["months_left"] = None
    goal["expected_pct"] = None
    goal["projected_date"] = None

    # Average monthly pace over the last 3 months, used for the projection.
    recent = goal.get("recent_cents") or 0
    start = parse_date(goal["start_date"])
    window_months = min(3.0, max(1.0, _months_between(start, ref)))
    goal["monthly_pace_cents"] = round(recent / window_months) if recent > 0 else 0
    if goal["remaining_cents"] and goal["monthly_pace_cents"] > 0:
        months_needed = goal["remaining_cents"] / goal["monthly_pace_cents"]
        goal["projected_date"] = (ref + dt.timedelta(days=round(months_needed * 30.4375))).isoformat()

    if saved >= target:
        goal["status"], goal["status_label"] = "done", "Completed"
        return goal
    if not goal["deadline"]:
        goal["status"], goal["status_label"] = "open", "No deadline"
        return goal

    deadline = parse_date(goal["deadline"])
    if deadline < ref:
        goal["status"], goal["status_label"] = "overdue", "Past deadline"
        goal["months_left"] = 0
        return goal
    # Whole calendar months until the deadline (at least one).
    months_left = (deadline.year - ref.year) * 12 + deadline.month - ref.month - (1 if deadline.day < ref.day else 0)
    months_left = max(1, months_left)
    goal["months_left"] = months_left
    goal["required_monthly_cents"] = -(-goal["remaining_cents"] // months_left)
    total_span = max(1, (deadline - start).days)
    elapsed = min(total_span, max(0, (ref - start).days))
    goal["expected_pct"] = elapsed / total_span * 100
    if goal["progress_pct"] + ON_TRACK_TOLERANCE >= goal["expected_pct"]:
        goal["status"], goal["status_label"] = "on_track", "On track"
    else:
        goal["status"], goal["status_label"] = "behind", "Behind schedule"
    return goal


GOAL_SQL = """
    SELECT g.*,
           COALESCE((SELECT SUM(amount_cents) FROM goal_contributions c WHERE c.goal_id = g.id), 0) AS saved_cents,
           COALESCE((SELECT SUM(amount_cents) FROM goal_contributions c
                     WHERE c.goal_id = g.id AND c.date > :recent_from), 0) AS recent_cents,
           (SELECT MAX(date) FROM goal_contributions c WHERE c.goal_id = g.id) AS last_contribution
    FROM savings_goals g
"""


def _params():
    return {"recent_from": add_months(today(), -3).isoformat()}


def list_goals(include_archived=False):
    sql = GOAL_SQL + (" " if include_archived else " WHERE g.is_archived = 0")
    sql += " ORDER BY g.is_archived, (g.deadline IS NULL), g.deadline, g.name COLLATE NOCASE"
    return [_enrich(dict(r)) for r in get_db().execute(sql, _params())]


def get_goal(goal_id):
    row = get_db().execute(GOAL_SQL + " WHERE g.id = :id", {**_params(), "id": goal_id}).fetchone()
    return _enrich(dict(row)) if row else None


def totals():
    goals = list_goals()
    return {
        "count": len(goals),
        "saved_cents": sum(g["saved_cents"] for g in goals),
        "target_cents": sum(g["target_cents"] for g in goals),
        "behind": [g for g in goals if g["status"] in ("behind", "overdue")],
    }


def _validate(form, goal_id=None):
    v = Validator(form)
    name = v.text("name", "Name", max_length=80)
    target = v.money("target", "Target amount")
    start = v.date("start_date", "Start date", required=False) or today().isoformat()
    deadline = v.date("deadline", "Deadline", required=False)
    notes = v.text("notes", "Notes", required=False, max_length=500)
    if deadline and deadline <= start:
        v.error("deadline", "The deadline must be after the start date.")
    if name:
        clash = get_db().execute(
            "SELECT id FROM savings_goals WHERE name = ? COLLATE NOCASE AND id IS NOT ?", (name, goal_id)
        ).fetchone()
        if clash:
            v.error("name", f"A goal called '{name}' already exists.")
    initial = None
    if goal_id is None:
        initial = v.money("initial", "Amount already saved", required=False, allow_zero=True)
    v.raise_if_errors()
    return {
        "name": name,
        "target_cents": target,
        "start_date": start,
        "deadline": deadline,
        "notes": notes,
        "is_archived": v.flag("is_archived"),
    }, initial


def create_goal(form):
    data, initial = _validate(form)
    db = get_db()
    goal_id = db.execute(
        """INSERT INTO savings_goals (name, target_cents, start_date, deadline, notes, is_archived)
           VALUES (:name, :target_cents, :start_date, :deadline, :notes, :is_archived)""",
        data,
    ).lastrowid
    if initial:
        db.execute(
            "INSERT INTO goal_contributions (goal_id, date, amount_cents, note) VALUES (?, ?, ?, ?)",
            (goal_id, data["start_date"], initial, "Starting balance"),
        )
    db.commit()
    return goal_id


def to_form(goal):
    return {
        "name": goal["name"],
        "target": cents_to_input(goal["target_cents"]),
        "start_date": goal["start_date"],
        "deadline": goal["deadline"] or "",
        "notes": goal["notes"] or "",
        "is_archived": "1" if goal["is_archived"] else "",
    }


def update_goal(goal_id, form):
    if not get_goal(goal_id):
        raise ValidationError("Goal not found.")
    data, _ = _validate(form, goal_id)
    data["id"] = goal_id
    db = get_db()
    db.execute(
        """UPDATE savings_goals SET name=:name, target_cents=:target_cents, start_date=:start_date,
               deadline=:deadline, notes=:notes, is_archived=:is_archived WHERE id=:id""",
        data,
    )
    db.commit()


def delete_goal(goal_id):
    db = get_db()
    if db.execute("DELETE FROM savings_goals WHERE id = ?", (goal_id,)).rowcount == 0:
        raise ValidationError("Goal not found.")
    db.commit()


def add_contribution(goal_id, form):
    goal = get_goal(goal_id)
    if not goal:
        raise ValidationError("Goal not found.")
    v = Validator(form)
    amount = v.money("amount")
    when = v.date("date", required=False) or today().isoformat()
    note = v.text("note", "Note", required=False, max_length=200)
    direction = v.choice("direction", "Direction", {"add": 1, "withdraw": -1}, required=False) or "add"
    if amount and direction == "withdraw" and amount > goal["saved_cents"]:
        v.error("amount", "You can't withdraw more than has been saved towards this goal.")
    v.raise_if_errors()
    db = get_db()
    db.execute(
        "INSERT INTO goal_contributions (goal_id, date, amount_cents, note) VALUES (?, ?, ?, ?)",
        (goal_id, when, amount if direction == "add" else -amount, note),
    )
    db.commit()


def contributions(goal_id):
    return [
        dict(r)
        for r in get_db().execute(
            "SELECT * FROM goal_contributions WHERE goal_id = ? ORDER BY date DESC, id DESC", (goal_id,)
        )
    ]


def delete_contribution(contribution_id):
    db = get_db()
    row = db.execute("SELECT goal_id FROM goal_contributions WHERE id = ?", (contribution_id,)).fetchone()
    if not row:
        raise ValidationError("Contribution not found.")
    db.execute("DELETE FROM goal_contributions WHERE id = ?", (contribution_id,))
    db.commit()
    return row["goal_id"]


def progress_series(goal_id):
    """Cumulative saved amount after each contribution date (for a chart)."""
    rows = get_db().execute(
        "SELECT date, SUM(amount_cents) AS amount FROM goal_contributions WHERE goal_id = ? GROUP BY date ORDER BY date",
        (goal_id,),
    )
    running, series = 0, []
    for r in rows:
        running += r["amount"]
        series.append({"date": r["date"], "saved_cents": running})
    return series
