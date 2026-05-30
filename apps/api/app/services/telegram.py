from __future__ import annotations

from fastapi import HTTPException
import httpx

from app.config import get_settings
from app.database import db
from app.utils import new_id, now_iso


RELATIONSHIP_OPTIONS = [
    ("romantic", "عاطفی"),
    ("ex", "اکس"),
    ("manager_colleague", "همکار/مدیر"),
    ("customer", "مشتری"),
    ("family", "خانواده"),
    ("friend", "دوست"),
]

GOAL_OPTIONS = [
    ("avoid_needy", "نیازمند به نظر نرسم"),
    ("set_boundary", "مرزبندی محترمانه"),
    ("calm_conflict", "آرام کردن تنش"),
    ("professional_reply", "پاسخ حرفه‌ای"),
    ("understand_only", "فقط بفهمم"),
]


async def send_telegram_message(chat_id: str | int, text: str, reply_markup: dict | None = None) -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        return
    payload: dict = {"chat_id": chat_id, "text": text, "parse_mode": "HTML"}
    if reply_markup:
        payload["reply_markup"] = reply_markup
    url = f"{settings.telegram_api_base_url.rstrip('/')}/bot{settings.telegram_bot_token}/sendMessage"
    headers = {}
    if settings.telegram_api_bypass_secret:
        headers["x-vercel-protection-bypass"] = settings.telegram_api_bypass_secret
    async with httpx.AsyncClient(timeout=10) as client:
        response = await client.post(url, json=payload, headers=headers)
    if response.status_code >= 400:
        raise HTTPException(status_code=502, detail="Telegram sendMessage failed")


def contact_keyboard() -> dict:
    return {
        "keyboard": [[{"text": "اشتراک‌گذاری شماره موبایل", "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def relationship_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": label, "callback_data": f"rel:{key}"}]
            for key, label in RELATIONSHIP_OPTIONS
        ]
    }


def goal_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": label, "callback_data": f"goal:{key}"}]
            for key, label in GOAL_OPTIONS
        ]
    }


def paid_keyboard(decode_id: str) -> dict:
    return {
        "inline_keyboard": [
            [{"text": "ساخت پاسخ قابل ارسال - ۱ اعتبار", "callback_data": f"paid:{decode_id}"}],
            [{"text": "شارژ اعتبار", "callback_data": "buy:credits_5"}],
        ]
    }


def buy_keyboard(payment_url: str) -> dict:
    return {"inline_keyboard": [[{"text": "پرداخت و شارژ اعتبار", "url": payment_url}]]}


def get_or_create_telegram_session(telegram_id: str, chat_id: str) -> dict:
    with db() as conn:
        row = conn.execute("SELECT * FROM telegram_sessions WHERE telegram_id = ?", (telegram_id,)).fetchone()
        if row:
            conn.execute(
                "UPDATE telegram_sessions SET chat_id = ?, updated_at = ? WHERE telegram_id = ?",
                (chat_id, now_iso(), telegram_id),
            )
            return dict(row)
        conn.execute(
            """
            INSERT INTO telegram_sessions (telegram_id, chat_id, state, created_at, updated_at)
            VALUES (?, ?, 'awaiting_contact', ?, ?)
            """,
            (telegram_id, chat_id, now_iso(), now_iso()),
        )
        return {
            "telegram_id": telegram_id,
            "chat_id": chat_id,
            "state": "awaiting_contact",
            "user_id": None,
            "ghost_mode": 0,
        }


def link_telegram_contact(
    telegram_id: str,
    chat_id: str,
    phone: str,
    referral_code: str | None = None,
) -> tuple[str, int, bool]:
    from app.services.auth import normalize_digits, generate_referral_code, _find_referrer

    normalized_phone = normalize_digits(phone)
    settings = get_settings()
    with db() as conn:
        user = conn.execute("SELECT * FROM users WHERE phone = ?", (normalized_phone,)).fetchone()
        created = False
        if user is None:
            user_id = new_id("user")
            balance = max(0, settings.signup_bonus_credits)
            referrer = _find_referrer(conn, referral_code)
            conn.execute(
                """
                INSERT INTO users (id, phone, telegram_id, created_at, credit_balance, source_channel, referral_code, referred_by_user_id)
                VALUES (?, ?, ?, ?, ?, 'telegram', ?, ?)
                """,
                (
                    user_id,
                    normalized_phone,
                    telegram_id,
                    now_iso(),
                    balance,
                    generate_referral_code(),
                    referrer["id"] if referrer else None,
                ),
            )
            if referrer:
                conn.execute(
                    "UPDATE users SET credit_balance = credit_balance + 5, referral_awarded_at = COALESCE(referral_awarded_at, ?) WHERE id = ?",
                    (now_iso(), referrer["id"]),
                )
            created = True
        else:
            user_id = str(user["id"])
            balance = int(user["credit_balance"])
            conn.execute("UPDATE users SET telegram_id = ? WHERE id = ?", (telegram_id, user_id))
            if not user["referral_code"]:
                conn.execute("UPDATE users SET referral_code = ? WHERE id = ?", (generate_referral_code(), user_id))

        conn.execute(
            """
            INSERT INTO telegram_sessions (telegram_id, user_id, chat_id, state, created_at, updated_at)
            VALUES (?, ?, ?, 'awaiting_message', ?, ?)
            ON CONFLICT(telegram_id) DO UPDATE SET
                user_id = excluded.user_id,
                chat_id = excluded.chat_id,
                state = 'awaiting_message',
                updated_at = excluded.updated_at
            """,
            (telegram_id, user_id, chat_id, now_iso(), now_iso()),
        )
        return user_id, balance, created


def get_or_create_referral(user_id: str) -> dict[str, str]:
    from app.services.auth import generate_referral_code

    with db() as conn:
        row = conn.execute("SELECT referral_code FROM users WHERE id = ?", (user_id,)).fetchone()
        code = row["referral_code"] if row else None
        if not code:
            code = generate_referral_code()
            conn.execute("UPDATE users SET referral_code = ? WHERE id = ?", (code, user_id))
    return {"code": str(code), "url": f"https://t.me/MeDecoderBot?start=ref_{code}"}


def create_session_token(user_id: str) -> str:
    token = new_id("sess")
    with db() as conn:
        conn.execute(
            "INSERT INTO auth_sessions (token, user_id, created_at) VALUES (?, ?, ?)",
            (token, user_id, now_iso()),
        )
    return token


def update_telegram_session(telegram_id: str, **fields: object) -> None:
    if not fields:
        return
    assignments = [f"{key} = ?" for key in fields]
    values = list(fields.values())
    assignments.append("updated_at = ?")
    values.append(now_iso())
    values.append(telegram_id)
    with db() as conn:
        conn.execute(
            f"UPDATE telegram_sessions SET {', '.join(assignments)} WHERE telegram_id = ?",
            values,
        )
