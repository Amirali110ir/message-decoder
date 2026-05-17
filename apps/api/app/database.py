from __future__ import annotations

import sqlite3
from contextlib import contextmanager
from pathlib import Path
from typing import Iterator

from app.config import get_settings


def _sqlite_path() -> str:
    url = get_settings().database_url
    if url.startswith("sqlite:///"):
        return url.replace("sqlite:///", "", 1)
    return "message_decoder.db"


@contextmanager
def db() -> Iterator[sqlite3.Connection]:
    path = _sqlite_path()
    if path not in (":memory:", ""):
        Path(path).parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(path)
    conn.row_factory = sqlite3.Row
    try:
        conn.execute("PRAGMA foreign_keys = ON")
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    with db() as conn:
        conn.executescript(
            """
            CREATE TABLE IF NOT EXISTS users (
                id TEXT PRIMARY KEY,
                phone TEXT UNIQUE,
                telegram_id TEXT UNIQUE,
                created_at TEXT NOT NULL,
                credit_balance INTEGER NOT NULL DEFAULT 0,
                consent_to_training INTEGER NOT NULL DEFAULT 0,
                source_channel TEXT NOT NULL DEFAULT 'web'
            );

            CREATE TABLE IF NOT EXISTS auth_otps (
                phone TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS auth_sessions (
                token TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS messages (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                raw_text TEXT,
                anonymized_text TEXT,
                relationship_type TEXT NOT NULL,
                user_goal TEXT NOT NULL,
                optional_context TEXT,
                privacy_consent TEXT NOT NULL,
                safety_label TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS decodes (
                id TEXT PRIMARY KEY,
                message_id TEXT NOT NULL,
                dominant_lens TEXT NOT NULL,
                secondary_lenses TEXT NOT NULL,
                confidence_level TEXT NOT NULL,
                free_output TEXT NOT NULL,
                paid_output TEXT,
                model_version TEXT NOT NULL,
                prompt_version TEXT NOT NULL,
                created_at TEXT NOT NULL,
                paid_at TEXT,
                FOREIGN KEY(message_id) REFERENCES messages(id)
            );

            CREATE TABLE IF NOT EXISTS payments (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                package_id TEXT NOT NULL,
                amount INTEGER NOT NULL,
                credits_added INTEGER NOT NULL,
                status TEXT NOT NULL,
                provider TEXT NOT NULL,
                authority TEXT,
                created_at TEXT NOT NULL,
                verified_at TEXT,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS feedback (
                id TEXT PRIMARY KEY,
                decode_id TEXT NOT NULL,
                user_rating TEXT,
                favorite_reply_label TEXT,
                copied_response INTEGER,
                sent_response TEXT,
                outcome TEXT,
                regret_score INTEGER,
                user_comment TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(decode_id) REFERENCES decodes(id)
            );

            CREATE TABLE IF NOT EXISTS copy_events (
                id TEXT PRIMARY KEY,
                decode_id TEXT NOT NULL,
                reply_label TEXT NOT NULL,
                reply_text_id TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(decode_id) REFERENCES decodes(id)
            );

            CREATE TABLE IF NOT EXISTS referrals (
                id TEXT PRIMARY KEY,
                referrer_user_id TEXT,
                referred_user_id TEXT,
                source TEXT,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS prompt_versions (
                id TEXT PRIMARY KEY,
                name TEXT NOT NULL,
                body TEXT NOT NULL,
                created_at TEXT NOT NULL,
                is_active INTEGER NOT NULL DEFAULT 1
            );

            CREATE TABLE IF NOT EXISTS analytics_events (
                id TEXT PRIMARY KEY,
                user_id TEXT,
                event_name TEXT NOT NULL,
                payload TEXT,
                created_at TEXT NOT NULL
            );
            """
        )

