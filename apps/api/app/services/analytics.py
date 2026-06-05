from __future__ import annotations

from datetime import datetime, timedelta, timezone

from app.database import db
from app.utils import dumps, new_id, now_iso


def track(event_name: str, user_id: str | None = None, payload: dict | None = None) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO analytics_events (id, user_id, event_name, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (new_id("evt"), user_id, event_name, dumps(payload or {}), now_iso()),
        )


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        dt = datetime.fromisoformat(value)
    except ValueError:
        return None
    return dt if dt.tzinfo else dt.replace(tzinfo=timezone.utc)


def retention_metrics(now: datetime | None = None) -> dict:
    """Return / retention metrics computed from real analytics_events.

    - d7_retention: of users whose first activity was >= 7 days ago, the share
      who came back at least 7 days after that first activity.
    - weekly_return_rate: of users active in the previous 7-day window
      (8–14 days ago), the share also active in the last 7 days.

    Anonymous events (user_id IS NULL) are ignored.
    """
    now = now or datetime.now(timezone.utc)
    week = timedelta(days=7)
    d7_cutoff = now - week
    prev_week_start = now - timedelta(days=14)
    prev_week_end = now - week

    with db() as conn:
        rows = conn.execute(
            "SELECT user_id, created_at FROM analytics_events WHERE user_id IS NOT NULL"
        ).fetchall()

    agg: dict[str, dict] = {}
    for row in rows:
        ts = _parse_iso(row["created_at"])
        if ts is None:
            continue
        uid = row["user_id"]
        rec = agg.setdefault(uid, {"first": ts, "last": ts, "prev_week": False, "last_week": False})
        rec["first"] = min(rec["first"], ts)
        rec["last"] = max(rec["last"], ts)
        if prev_week_start <= ts < prev_week_end:
            rec["prev_week"] = True
        if ts >= prev_week_end:
            rec["last_week"] = True

    d7_cohort = [r for r in agg.values() if r["first"] <= d7_cutoff]
    d7_retained = [r for r in d7_cohort if (r["last"] - r["first"]) >= week]

    weekly_cohort = [r for r in agg.values() if r["prev_week"]]
    weekly_returned = [r for r in weekly_cohort if r["last_week"]]

    def _rate(num: int, den: int) -> float:
        return (num / den) if den else 0.0

    return {
        "d7_retention": {
            "cohort": len(d7_cohort),
            "retained": len(d7_retained),
            "rate": _rate(len(d7_retained), len(d7_cohort)),
        },
        "weekly_return": {
            "cohort": len(weekly_cohort),
            "returned": len(weekly_returned),
            "rate": _rate(len(weekly_returned), len(weekly_cohort)),
        },
    }


def usage_frequency() -> dict:
    """Per-user usage frequency — the habit signal for T2.3.

    - active_users: users with >= 1 event
    - avg_actions_per_user: mean events per active user
    - multi_action_rate: share of active users with >= 2 actions (returning to
      the tool rather than one-and-done)
    - before_send_checks: total before-send checks (the habit feature)
    """
    with db() as conn:
        rows = conn.execute(
            "SELECT user_id, event_name FROM analytics_events WHERE user_id IS NOT NULL"
        ).fetchall()

    per_user: dict[str, int] = {}
    before_send = 0
    for row in rows:
        per_user[row["user_id"]] = per_user.get(row["user_id"], 0) + 1
        if row["event_name"] == "before_send_checked":
            before_send += 1

    active = len(per_user)
    total_actions = sum(per_user.values())
    multi = sum(1 for c in per_user.values() if c >= 2)
    return {
        "active_users": active,
        "avg_actions_per_user": (total_actions / active) if active else 0.0,
        "multi_action_rate": (multi / active) if active else 0.0,
        "before_send_checks": before_send,
    }

