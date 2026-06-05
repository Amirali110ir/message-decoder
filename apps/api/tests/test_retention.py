"""Deterministic test for retention metrics (T2.1) on a fresh isolated DB."""

import os

os.environ["DATABASE_URL"] = "sqlite:///./test_retention.db"

from datetime import datetime, timedelta, timezone

from app.database import db, init_db
from app.services.analytics import retention_metrics
from app.utils import new_id


NOW = datetime(2026, 6, 2, 12, 0, 0, tzinfo=timezone.utc)


def setup_module():
    try:
        os.remove("test_retention.db")
    except FileNotFoundError:
        pass
    init_db()


def _event(user_id: str | None, when: datetime) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO analytics_events (id, user_id, event_name, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (new_id("evt"), user_id, "x", "{}", when.isoformat()),
        )


def test_retention_metrics_compute_from_real_events():
    # u_retained: first activity 10 days ago, came back today -> D7 retained.
    _event("u_retained", NOW - timedelta(days=10))
    _event("u_retained", NOW - timedelta(hours=1))
    # u_churned: only active 8 days ago, never returned -> in cohort, not retained.
    _event("u_churned", NOW - timedelta(days=8))
    # u_new: first seen yesterday -> not yet in the D7 cohort.
    _event("u_new", NOW - timedelta(days=1))
    # anonymous events are ignored entirely.
    _event(None, NOW - timedelta(days=10))

    m = retention_metrics(now=NOW)

    # D7 cohort = users first seen >= 7d ago = {u_retained, u_churned}
    assert m["d7_retention"]["cohort"] == 2
    assert m["d7_retention"]["retained"] == 1
    assert abs(m["d7_retention"]["rate"] - 0.5) < 1e-9

    # Weekly return: prev-week-active (8-14d ago) = {u_retained, u_churned};
    # of those, active in last 7d = {u_retained} -> 1/2.
    assert m["weekly_return"]["cohort"] == 2
    assert m["weekly_return"]["returned"] == 1
    assert abs(m["weekly_return"]["rate"] - 0.5) < 1e-9


def test_retention_metrics_empty_is_zero():
    # A now far in the future where no one is in any cohort still returns zeros,
    # never divides by zero.
    m = retention_metrics(now=NOW + timedelta(days=365))
    assert m["weekly_return"]["rate"] == 0.0
    assert isinstance(m["d7_retention"]["rate"], float)
