import json
import sqlite3
from datetime import datetime
from typing import Any, Optional

from app.config import get_settings
from app.database import db


def _now_iso() -> str:
    return datetime.utcnow().isoformat(timespec='seconds')


def get_cached_response(task: str, cache_key: str) -> Optional[dict[str, Any]]:
    """Retrieve a cached response for the given task and cache_key.
    Returns the stored JSON object if found, otherwise None.
    """
    settings = get_settings()
    if not settings.ai_semantic_cache_enabled:
        return None
    with db() as conn:
        cur = conn.execute(
            "SELECT response_json, hit_count FROM semantic_cache WHERE cache_key = ? AND task = ?",
            (cache_key, task),
        )
        row = cur.fetchone()
        if row:
            # Increment hit count and update last_hit_at
            conn.execute(
                "UPDATE semantic_cache SET hit_count = hit_count + 1, last_hit_at = ? WHERE cache_key = ?",
                (_now_iso(), cache_key),
            )
            try:
                return json.loads(row["response_json"])
            except json.JSONDecodeError:
                return None
    return None


def set_cached_response(
    task: str, cache_key: str, response: dict[str, Any], model_used: str | None = None
) -> None:
    """Store a response in the semantic cache.
    If the key already exists, it will be overwritten (useful for version upgrades).
    """
    settings = get_settings()
    if not settings.ai_semantic_cache_enabled:
        return
    response_json = json.dumps(response, ensure_ascii=False)
    now = _now_iso()
    with db() as conn:
        conn.execute(
            "INSERT OR REPLACE INTO semantic_cache (cache_key, task, response_json, model_used, hit_count, created_at, last_hit_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                cache_key,
                task,
                response_json,
                model_used,
                0,
                now,
                now,
            ),
        )
