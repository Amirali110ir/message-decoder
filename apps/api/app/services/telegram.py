from __future__ import annotations

import re

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

RELATIONSHIP_LABELS = dict(RELATIONSHIP_OPTIONS)
GOAL_LABELS = dict(GOAL_OPTIONS)

LENS_FA = {
    "dopamine": "هدف و کنترل",
    "oxytocin": "امنیت و اعتماد",
    "serotonin": "شأن و احترام",
}
# Lens emoji mirrors the three-lens colours in the design (amber/rose/violet).
LENS_EMOJI = {"dopamine": "🟠", "oxytocin": "🌹", "serotonin": "🟣"}

_FA_DIGITS = str.maketrans("0123456789", "۰۱۲۳۴۵۶۷۸۹")


def fa_num(value) -> str:
    """Render any number with Persian digits (matches the prototype's faNum)."""
    return str(value).translate(_FA_DIGITS)


# ---- UX copy (verbatim from the design handoff: tg-data.jsx) ----
WELCOME_TEXT = (
    "سلام 👋 من <b>Message Decoder</b>ام.\n\n"
    "هر پیامی که نمی‌دونی پشتش چی خوابیده، برام <b>فوروارد کن</b> — قبل از اینکه جواب بدی، "
    "طرف رو برات می‌خونم: لحن، نیتِ پنهان، و یه جوابِ خوب.\n\n"
    "همین حالا یه پیام رو فوروارد کن تا با هم ببینیم."
)

FORWARD_HINT = "برای شروع، یه پیام برام <b>فوروارد کن</b> 👇 اون‌وقت تحلیلش می‌کنم."


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


async def answer_callback(callback_query_id: str | None) -> None:
    settings = get_settings()
    if not settings.telegram_bot_token or not callback_query_id:
        return
    url = f"{settings.telegram_api_base_url.rstrip('/')}/bot{settings.telegram_bot_token}/answerCallbackQuery"
    headers = {}
    if settings.telegram_api_bypass_secret:
        headers["x-vercel-protection-bypass"] = settings.telegram_api_bypass_secret
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"callback_query_id": callback_query_id}, headers=headers)
    except httpx.HTTPError:
        pass


def _esc(value: str | None) -> str:
    return (
        str(value or "")
        .replace("&", "&amp;")
        .replace("<", "&lt;")
        .replace(">", "&gt;")
    )


def contact_keyboard() -> dict:
    return {
        "keyboard": [[{"text": "اشتراک‌گذاری شماره موبایل", "request_contact": True}]],
        "resize_keyboard": True,
        "one_time_keyboard": True,
    }


def _chunk(items: list[dict], size: int = 2) -> list[list[dict]]:
    return [items[i : i + size] for i in range(0, len(items), size)]


def relationship_keyboard(prefix: str = "rel") -> dict:
    buttons = [{"text": label, "callback_data": f"{prefix}:{key}"} for key, label in RELATIONSHIP_OPTIONS]
    return {"inline_keyboard": _chunk(buttons, 2)}


def goal_keyboard() -> dict:
    buttons = [{"text": label, "callback_data": f"goal:{key}"} for key, label in GOAL_OPTIONS]
    return {"inline_keyboard": _chunk(buttons, 2)}


def paid_keyboard(decode_id: str) -> dict:
    return {
        "inline_keyboard": [
            [{"text": "ساخت پاسخ قابل ارسال - ۱ اعتبار", "callback_data": f"paid:{decode_id}"}],
            [{"text": "شارژ اعتبار", "callback_data": "buy:credits_5"}],
        ]
    }


def buy_keyboard(payment_url: str) -> dict:
    return {"inline_keyboard": [[{"text": "پرداخت و شارژ اعتبار", "url": payment_url}]]}


# ============================================================
#  Design-handoff conversation: keyboards, cards, extraction
#  (node graph mirrored from tg-data.jsx → NODES)
# ============================================================

def web_url(slug: str | None = None) -> str:
    base = get_settings().web_app_base_url.rstrip("/")
    return f"{base}/decoder" if not slug else f"{base}/c/{slug}"


def decode_keyboard(memory: bool = False) -> dict:
    """Keyboard after an analysis card (NODES.decode1 / memory-aware decode)."""
    rows = [
        [{"text": "🎯 رابطه و هدف رو می‌گم", "callback_data": "n:askrel"}],
        [
            {"text": "💬 جواب پیشنهادی", "callback_data": "n:replies"},
            {"text": "🔍 یعنی چی؟", "callback_data": "n:translate"},
        ],
        [{"text": "🧬 چه‌جور آدمیه؟", "callback_data": "n:personality"}],
    ]
    if memory:
        rows.append([{"text": "🌐 باز کن در وب", "url": web_url()}])
    else:
        rows.append([
            {"text": "👤 ذخیرهٔ فرستنده", "callback_data": "n:save"},
            {"text": "🌐 وب", "url": web_url()},
        ])
    return {"inline_keyboard": rows}


def deeper_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "💬 جواب پیشنهادی بده", "callback_data": "n:replies"}],
            [
                {"text": "👤 ذخیرهٔ فرستنده", "callback_data": "n:save"},
                {"text": "🔍 یعنی چی؟", "callback_data": "n:translate"},
            ],
        ]
    }


def tone_keyboard(saved: bool = False) -> dict:
    rows = [[
        {"text": "نرم‌تر", "callback_data": "tone:softer"},
        {"text": "قاطع‌تر", "callback_data": "tone:firmer"},
        {"text": "کوتاه‌تر", "callback_data": "tone:shorter"},
    ]]
    if saved:
        rows.append([{"text": "🌐 باز کن در وب", "url": web_url()}])
    else:
        rows.append([
            {"text": "👤 ذخیرهٔ فرستنده", "callback_data": "n:save"},
            {"text": "🌐 وب", "url": web_url()},
        ])
    return {"inline_keyboard": rows}


def translate_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "💬 حالا یه جواب بده", "callback_data": "n:replies"}],
            [{"text": "👤 ذخیرهٔ فرستنده", "callback_data": "n:save"}],
        ]
    }


def personality_keyboard(memory: bool) -> dict:
    if memory:
        return {
            "inline_keyboard": [
                [{"text": "💬 با این تصویر، جواب بده", "callback_data": "n:replies"}],
                [{"text": "🌐 پروفایلش در وب", "url": web_url()}],
            ]
        }
    return {
        "inline_keyboard": [
            [{"text": "👤 ذخیره‌ش کن تا دقیق‌تر بشه", "callback_data": "n:save"}],
            [{"text": "💬 جواب پیشنهادی", "callback_data": "n:replies"}],
        ]
    }


def save_ask_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "➕ آره، اضافه کن", "callback_data": "save:yes"}],
            [
                {"text": "الان نه", "callback_data": "save:later"},
                {"text": "🛡️ حریم خصوصی", "callback_data": "save:privacy"},
            ],
        ]
    }


def save_note_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "زود می‌رنجه، سرد می‌شه", "callback_data": "note:cold"}],
            [{"text": "براش اولویت مهمه", "callback_data": "note:priority"}],
            [{"text": "بدونِ یادداشت", "callback_data": "note:none"}],
        ]
    }


SAVE_NOTE_TEXTS = {
    "cold": "زود می‌رنجه و سرد می‌شه",
    "priority": "حساسه به اینکه در اولویت باشه",
    "none": "—",
}


def save_done_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "📨 یه پیامِ دیگه ازش فوروارد کن", "callback_data": "n:nextforward"}],
            [
                {"text": "🧬 حالا شخصیتش رو بخون", "callback_data": "n:personality"},
                {"text": "🌐 وب", "url": web_url()},
            ],
        ]
    }


def save_later_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "➕ حالا اضافه‌ش کن", "callback_data": "save:yes"}],
            [{"text": "💬 جواب پیشنهادی", "callback_data": "n:replies"}],
        ]
    }


def privacy_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [
                {"text": "بله، بدونِ نام", "callback_data": "pc:anon"},
                {"text": "تاریخچهٔ من", "callback_data": "pc:history"},
            ],
            [
                {"text": "فقط پردازش", "callback_data": "pc:none"},
                {"text": "👻 حالتِ شبح", "callback_data": "n:ghost"},
            ],
        ]
    }


def privacy_set_keyboard() -> dict:
    return {"inline_keyboard": [[{"text": "➕ برگرد به ذخیرهٔ فرستنده", "callback_data": "save:yes"}]]}


def reminder_keyboard() -> dict:
    return {
        "inline_keyboard": [
            [{"text": "⏰ آره، یادآور بذار", "callback_data": "n:reminder"}],
            [
                {"text": "💬 چه جوابی بدم؟", "callback_data": "n:replies"},
                {"text": "🌐 وب", "url": web_url()},
            ],
        ]
    }


# ---- analysis card rendered as a structured text message (design §3 fallback) ----
def render_analysis_card(free_output: dict, *, memory: bool, sender_name: str | None) -> str:
    lens = free_output.get("dominant_lens") or {}
    dominant_key = lens.get("key") or "oxytocin"
    dominant_fa = lens.get("fa") or LENS_FA.get(dominant_key, "—")
    mix = free_output.get("lens_mix") or {}
    tone = free_output.get("tone_stress") or {}
    confidence = free_output.get("confidence") or "متوسط"
    subtext = (
        free_output.get("insight_line")
        or free_output.get("likely_underlying_need")
        or "—"
    )

    def bar(pct: int) -> str:
        filled = max(0, min(10, round(int(pct) / 10)))
        return "█" * filled + "░" * (10 - filled)

    lines = [
        f"{LENS_EMOJI.get(dominant_key, '🔎')} <b>لنز غالب: {dominant_fa}</b>",
        f"اطمینان: {confidence}",
        "",
        "<b>ترکیبِ سه لنز:</b>",
    ]
    for key in ("dopamine", "oxytocin", "serotonin"):
        pct = int(mix.get(key, 0))
        lines.append(f"{LENS_EMOJI[key]} {LENS_FA[key]}  <code>{bar(pct)}</code> {fa_num(pct)}٪")
    intensity = int(tone.get("intensity", 0))
    lines += [
        "",
        f"📊 فشارِ مکالمه: <b>{tone.get('label', 'مبهم')}</b> — {fa_num(intensity)}٪",
        "",
        f"<b>زیرمتن:</b> {subtext}",
    ]
    if memory and sender_name:
        lines.append(f"\n🧠 <i>بر پایهٔ کل تاریخچهٔ {sender_name} — با حافظهٔ رابطه</i>")
    else:
        lines.append("\n✨ <i>خواندنِ سریع</i>")
    return "\n".join(lines)


# ---- extract dates / phone numbers from a forwarded message (NODES.decode2) ----
_PHONE_RE = re.compile(r"(?<![\d۰-۹])((?:0|۰)?(?:9|۹)[\d۰-۹\s\-]{8,12})(?![\d۰-۹])")
_TIME_RE = re.compile(r"ساعت\s*[\d۰-۹]{1,2}(?:[:٫][\d۰-۹]{1,2})?")
_DAY_RE = re.compile(r"(شنبه|یکشنبه|دوشنبه|سه‌شنبه|سه شنبه|چهارشنبه|پنجشنبه|پنج‌شنبه|جمعه|امروز|فردا|پس‌فردا)")


def _to_fa_phone(raw: str) -> str:
    digits = re.sub(r"\D", "", raw.translate(str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")))
    if digits.startswith("98"):
        digits = "0" + digits[2:]
    if len(digits) == 10 and digits.startswith("9"):
        digits = "0" + digits
    if len(digits) == 11:
        grouped = f"{digits[0:4]} {digits[4:7]} {digits[7:11]}"
        return fa_num(grouped)
    return fa_num(digits)


def extract_info(text: str, sender_name: str | None = None) -> list[dict]:
    items: list[dict] = []
    day = _DAY_RE.search(text)
    time = _TIME_RE.search(text)
    if day or time:
        when = " ".join(part for part in [day.group(0) if day else "", time.group(0) if time else ""] if part).strip()
        items.append({
            "icon": "⏰",
            "value": fa_num(when),
            "label": "زمانِ دعوت — می‌تونی یادآور بذاری",
        })
    phone = _PHONE_RE.search(text)
    if phone:
        who = f"شمارهٔ جدیدِ {sender_name}" if sender_name else "شمارهٔ جدید"
        items.append({
            "icon": "☎️",
            "value": _to_fa_phone(phone.group(1)),
            "label": f"{who} — ذخیره در مخاطب",
        })
    return items


def render_info(items: list[dict]) -> str:
    lines = ["📌 دو چیز توی این پیام بود که شاید بخوای نگه‌داری:\n"]
    for it in items:
        lines.append(f"{it['icon']} <b>{it['value']}</b>\n    {it['label']}")
    return "\n".join(lines)


def detect_forward_sender(message: dict) -> tuple[str | None, str | None]:
    """Return (display_name, sender_id) for a forwarded message, if any."""
    origin = message.get("forward_origin") or {}
    if origin:
        if origin.get("type") == "user":
            user = origin.get("sender_user") or {}
            name = " ".join(part for part in [user.get("first_name"), user.get("last_name")] if part).strip()
            return (name or user.get("username"), str(user.get("id") or "") or None)
        if origin.get("type") == "hidden_user":
            return (origin.get("sender_user_name"), None)
        if origin.get("type") in ("chat", "channel"):
            chat = origin.get("sender_chat") or origin.get("chat") or {}
            return (chat.get("title"), str(chat.get("id") or "") or None)
    legacy = message.get("forward_from") or {}
    if legacy:
        name = " ".join(part for part in [legacy.get("first_name"), legacy.get("last_name")] if part).strip()
        return (name or legacy.get("username"), str(legacy.get("id") or "") or None)
    if message.get("forward_sender_name"):
        return (message.get("forward_sender_name"), None)
    return (None, None)


def upsert_contact_from_telegram(
    user_id: str,
    name: str,
    relationship_type: str,
    note: str | None,
) -> str:
    """Create/find a contact in the SHARED web DB (web↔telegram parity)."""
    with db() as conn:
        existing = conn.execute(
            "SELECT id FROM contacts WHERE user_id = ? AND lower(name) = lower(?)",
            (user_id, name),
        ).fetchone()
        if existing:
            conn.execute(
                "UPDATE contacts SET relationship_type = ?, profile_summary = COALESCE(?, profile_summary), updated_at = ? WHERE id = ?",
                (relationship_type, note if note and note != "—" else None, now_iso(), existing["id"]),
            )
            return str(existing["id"])
        contact_id = new_id("ct")
        created_at = now_iso()
        conn.execute(
            """
            INSERT INTO contacts (
                id, user_id, name, relationship_type, default_goal, profile_summary,
                interaction_count, created_at, updated_at
            ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
            """,
            (
                contact_id,
                user_id,
                name,
                relationship_type,
                None,
                (note if note and note != "—" else f"از تلگرام ذخیره شد: {name}."),
                created_at,
                created_at,
            ),
        )
        return contact_id


def append_contact_note(user_id: str, contact_id: str, note: str) -> None:
    """Append a short note (e.g. a saved phone) to a contact's profile summary."""
    with db() as conn:
        row = conn.execute(
            "SELECT profile_summary FROM contacts WHERE id = ? AND user_id = ?",
            (contact_id, user_id),
        ).fetchone()
        if not row:
            return
        existing = (row["profile_summary"] or "").strip()
        if note in existing:
            return
        merged = f"{existing} | {note}".strip(" |") if existing else note
        conn.execute(
            "UPDATE contacts SET profile_summary = ?, updated_at = ? WHERE id = ? AND user_id = ?",
            (merged[:2000], now_iso(), contact_id, user_id),
        )


def get_contact_memory_summary(user_id: str, contact_id: str) -> tuple[str | None, str | None]:
    with db() as conn:
        row = conn.execute(
            "SELECT name, memory_summary, profile_summary FROM contacts WHERE id = ? AND user_id = ?",
            (contact_id, user_id),
        ).fetchone()
    if not row:
        return (None, None)
    return (row["name"], row["memory_summary"] or row["profile_summary"])


async def send_chat_action(chat_id: str | int, action: str = "typing") -> None:
    settings = get_settings()
    if not settings.telegram_bot_token:
        return
    url = f"{settings.telegram_api_base_url.rstrip('/')}/bot{settings.telegram_bot_token}/sendChatAction"
    headers = {}
    if settings.telegram_api_bypass_secret:
        headers["x-vercel-protection-bypass"] = settings.telegram_api_bypass_secret
    try:
        async with httpx.AsyncClient(timeout=10) as client:
            await client.post(url, json={"chat_id": chat_id, "action": action}, headers=headers)
    except httpx.HTTPError:
        # Typing indicator is best-effort; never block the real reply on it.
        pass


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
