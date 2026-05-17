from __future__ import annotations

from fastapi import Header, HTTPException

from app.database import db
from app.utils import new_id, now_iso


def create_or_update_otp(phone: str, code: str) -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO auth_otps (phone, code, created_at)
            VALUES (?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET code = excluded.code, created_at = excluded.created_at
            """,
            (phone, code, now_iso()),
        )


def verify_otp(phone: str, code: str) -> tuple[str, str, int]:
    with db() as conn:
        otp = conn.execute("SELECT code FROM auth_otps WHERE phone = ?", (phone,)).fetchone()
        if not otp or otp["code"] != code:
            raise HTTPException(status_code=401, detail="Invalid OTP code")

        user = conn.execute("SELECT * FROM users WHERE phone = ?", (phone,)).fetchone()
        if user is None:
            user_id = new_id("user")
            conn.execute(
                "INSERT INTO users (id, phone, created_at, credit_balance, source_channel) VALUES (?, ?, ?, 0, 'web')",
                (user_id, phone, now_iso()),
            )
            credit_balance = 0
        else:
            user_id = user["id"]
            credit_balance = int(user["credit_balance"])

        token = new_id("sess")
        conn.execute(
            "INSERT INTO auth_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, now_iso()),
        )
        return token, user_id, credit_balance


def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    with db() as conn:
        row = conn.execute("SELECT user_id FROM auth_sessions WHERE token = ?", (token,)).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    return str(row["user_id"])

