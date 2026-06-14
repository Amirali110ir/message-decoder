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
                source_channel TEXT NOT NULL DEFAULT 'web',
                referral_code TEXT UNIQUE,
                referred_by_user_id TEXT,
                referral_awarded_at TEXT
            );

            CREATE TABLE IF NOT EXISTS auth_otps (
                phone TEXT PRIMARY KEY,
                code TEXT NOT NULL,
                created_at TEXT NOT NULL,
                expires_at TEXT,
                attempts INTEGER NOT NULL DEFAULT 0,
                consumed_at TEXT
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
                free_model_version TEXT,
                paid_model_version TEXT,
                prompt_version TEXT NOT NULL,
                rule_engine_version TEXT,
                output_schema_version TEXT,
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

            CREATE TABLE IF NOT EXISTS quality_signals (
                id TEXT PRIMARY KEY,
                decode_id TEXT NOT NULL,
                signal_name TEXT NOT NULL,
                signal_value TEXT NOT NULL,
                weight REAL NOT NULL DEFAULT 1,
                source TEXT NOT NULL,
                created_at TEXT NOT NULL,
                FOREIGN KEY(decode_id) REFERENCES decodes(id)
            );

            CREATE TABLE IF NOT EXISTS daily_learning_reports (
                id TEXT PRIMARY KEY,
                report_date TEXT NOT NULL,
                metrics TEXT NOT NULL,
                recommendations TEXT NOT NULL,
                created_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS semantic_cache (
                cache_key TEXT PRIMARY KEY,
                task TEXT NOT NULL,
                response_json TEXT NOT NULL,
                model_used TEXT,
                hit_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                last_hit_at TEXT
            );

            CREATE TABLE IF NOT EXISTS contacts (
                id TEXT PRIMARY KEY,
                user_id TEXT NOT NULL,
                name TEXT NOT NULL,
                relationship_type TEXT NOT NULL,
                default_goal TEXT,
                profile_summary TEXT,
                interaction_count INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id) ON DELETE CASCADE
            );

            CREATE TABLE IF NOT EXISTS telegram_sessions (
                telegram_id TEXT PRIMARY KEY,
                user_id TEXT,
                chat_id TEXT NOT NULL,
                state TEXT NOT NULL,
                message_text TEXT,
                relationship_type TEXT,
                user_goal TEXT,
                decode_id TEXT,
                ghost_mode INTEGER NOT NULL DEFAULT 0,
                created_at TEXT NOT NULL,
                updated_at TEXT NOT NULL,
                FOREIGN KEY(user_id) REFERENCES users(id)
            );

            CREATE TABLE IF NOT EXISTS admin_login_attempts (
                phone TEXT PRIMARY KEY,
                failed_count INTEGER NOT NULL DEFAULT 0,
                locked_until TEXT,
                updated_at TEXT NOT NULL
            );

            CREATE TABLE IF NOT EXISTS sms_send_logs (
                id TEXT PRIMARY KEY,
                provider TEXT NOT NULL,
                purpose TEXT NOT NULL,
                phone TEXT NOT NULL,
                template_id TEXT,
                message_id TEXT,
                status TEXT NOT NULL,
                request_payload TEXT,
                response_payload TEXT,
                error_message TEXT,
                created_at TEXT NOT NULL
            );
            """
        )
        _ensure_column(conn, "auth_otps", "expires_at", "TEXT")
        _ensure_column(conn, "auth_otps", "attempts", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "auth_otps", "consumed_at", "TEXT")
        _ensure_column(conn, "users", "referral_code", "TEXT")
        _ensure_column(conn, "users", "referred_by_user_id", "TEXT")
        _ensure_column(conn, "users", "referral_awarded_at", "TEXT")
        conn.execute("CREATE UNIQUE INDEX IF NOT EXISTS idx_users_referral_code ON users(referral_code)")
        _ensure_column(conn, "decodes", "free_model_version", "TEXT")
        _ensure_column(conn, "decodes", "paid_model_version", "TEXT")
        _ensure_column(conn, "decodes", "rule_engine_version", "TEXT")
        _ensure_column(conn, "decodes", "output_schema_version", "TEXT")
        _ensure_column(conn, "messages", "contact_id", "TEXT")
        _ensure_column(conn, "messages", "message_focus", "TEXT")
        _ensure_column(conn, "feedback", "selected_reply_label", "TEXT")
        _ensure_column(conn, "payments", "ref_id", "TEXT")
        _ensure_column(conn, "contacts", "memory_json", "TEXT")
        _ensure_column(conn, "contacts", "memory_summary", "TEXT")
        _ensure_column(conn, "contacts", "updated_at", "TEXT")
        _ensure_column(conn, "telegram_sessions", "pending_referral_code", "TEXT")
        # Rich conversation state for the design-handoff Telegram flow.
        _ensure_column(conn, "telegram_sessions", "forward_from_name", "TEXT")
        _ensure_column(conn, "telegram_sessions", "forward_from_id", "TEXT")
        _ensure_column(conn, "telegram_sessions", "contact_id", "TEXT")
        _ensure_column(conn, "telegram_sessions", "memory_on", "INTEGER NOT NULL DEFAULT 0")
        _ensure_column(conn, "telegram_sessions", "consent", "TEXT")
        _ensure_column(conn, "telegram_sessions", "last_free_json", "TEXT")
        _ensure_column(conn, "telegram_sessions", "pending_note", "TEXT")
        _ensure_column(conn, "telegram_sessions", "last_reply_text", "TEXT")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sms_send_logs_created_at ON sms_send_logs(created_at)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_sms_send_logs_provider_status ON sms_send_logs(provider, status)")


def _ensure_column(conn: sqlite3.Connection, table: str, column: str, definition: str) -> None:
    columns = {row["name"] for row in conn.execute(f"PRAGMA table_info({table})")}
    if column not in columns:
        conn.execute(f"ALTER TABLE {table} ADD COLUMN {column} {definition}")
