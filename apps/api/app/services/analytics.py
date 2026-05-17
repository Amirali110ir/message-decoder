from __future__ import annotations

from app.database import db
from app.utils import dumps, new_id, now_iso


def track(event_name: str, user_id: str | None = None, payload: dict | None = None) -> None:
    with db() as conn:
        conn.execute(
            "INSERT INTO analytics_events (id, user_id, event_name, payload, created_at) VALUES (?, ?, ?, ?, ?)",
            (new_id("evt"), user_id, event_name, dumps(payload or {}), now_iso()),
        )

