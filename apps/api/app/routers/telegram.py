from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.schemas import FreeDecodeIn, FreeDecodeOutput, GhostPaidDecodeIn, PaidDecodeIn
from app.routers.decode import create_free_decode, create_ghost_paid_decode, create_paid_decode
from app.services.payments import create_payment
from app.services import telegram as tg
from app.utils import dumps, loads

router = APIRouter(prefix="/telegram", tags=["telegram"])

# Tone targets exposed by the design's «نرم‌تر/قاطع‌تر/کوتاه‌تر» buttons.
TONE_FA = {"softer": "نرم‌تر", "firmer": "قاطع‌تر", "shorter": "کوتاه‌تر"}
# Session consent token → schema PrivacyConsent literal.
_CONSENT_TO_PRIVACY = {"anon": "anonymized", "history": "history", "none": "none"}


@router.post("/webhook")
async def telegram_webhook(
    update: dict[str, Any],
    x_telegram_bot_api_secret_token: str | None = Header(default=None),
) -> dict[str, bool]:
    settings = get_settings()
    if settings.telegram_webhook_secret and x_telegram_bot_api_secret_token != settings.telegram_webhook_secret:
        raise HTTPException(status_code=401, detail="Invalid Telegram webhook secret")

    if "message" in update:
        await _handle_message(update["message"])
    elif "callback_query" in update:
        await _handle_callback(update["callback_query"])
    return {"ok": True}


def _parse_start_referral(text: str) -> str | None:
    parts = text.split(maxsplit=1)
    if len(parts) < 2:
        return None
    payload = parts[1].strip()
    if not payload.startswith("ref_"):
        return None
    code = payload.removeprefix("ref_").strip().upper()
    return code or None


# ============================================================
#  Incoming messages
# ============================================================
async def _handle_message(message: dict[str, Any]) -> None:
    chat_id = str(message.get("chat", {}).get("id") or "")
    from_user = message.get("from") or {}
    telegram_id = str(from_user.get("id") or "")
    if not chat_id or not telegram_id:
        return

    session = tg.get_or_create_telegram_session(telegram_id, chat_id)
    text = (message.get("text") or "").strip()
    contact = message.get("contact")

    if text.startswith("/start"):
        referral_code = _parse_start_referral(text)
        if referral_code and not session.get("user_id"):
            tg.update_telegram_session(telegram_id, pending_referral_code=referral_code)
        if session.get("user_id"):
            await tg.send_telegram_message(chat_id, tg.WELCOME_TEXT)
        else:
            intro = "به Message Decoder خوش آمدی. برای شروع، شماره موبایلت را با دکمه زیر تایید کن."
            if referral_code:
                intro = f"با کد معرفی {referral_code} وارد شدی. شماره موبایلت را تایید کن تا اعتبار هدیه فعال شود."
            await tg.send_telegram_message(chat_id, intro, tg.contact_keyboard())
        return

    if text.startswith("/referral"):
        if not session.get("user_id"):
            await tg.send_telegram_message(chat_id, "اول با /start شماره‌ات را وصل کن تا کد معرفی اختصاصی بگیری.", tg.contact_keyboard())
            return
        referral = tg.get_or_create_referral(str(session["user_id"]))
        await tg.send_telegram_message(
            chat_id,
            f"کد معرفی تو:\n<b>{referral['code']}</b>\n\nلینک دعوت:\n{referral['url']}\n\nهر شماره جدیدی که با این کد ثبت‌نام کند، ۵ اعتبار برای تو فعال می‌شود.",
        )
        return

    if text.startswith("/cancel"):
        tg.update_telegram_session(
            telegram_id,
            state="awaiting_message",
            message_text=None,
            relationship_type=None,
            user_goal=None,
            decode_id=None,
            ghost_mode=0,
        )
        await tg.send_telegram_message(chat_id, "لغو شد. پیام بعدی را بفرست.")
        return

    if text.startswith("/ghost"):
        tg.update_telegram_session(telegram_id, ghost_mode=1, state="awaiting_message")
        await tg.send_telegram_message(chat_id, "👻 حالتِ شبح برای پیام بعدی روشن شد. متن را بفرست؛ تحلیل و پاسخ در تاریخچه ذخیره نمی‌شود.")
        return

    if contact:
        contact_user_id = str(contact.get("user_id") or "")
        if contact_user_id and contact_user_id != telegram_id:
            await tg.send_telegram_message(chat_id, "برای امنیت، فقط شماره خودت را می‌توانی وصل کنی.")
            return
        phone = str(contact.get("phone_number") or "")
        if not phone:
            await tg.send_telegram_message(chat_id, "شماره دریافت نشد. دوباره از دکمه اشتراک‌گذاری شماره استفاده کن.")
            return
        pending_referral = session.get("pending_referral_code")
        _, balance, created = tg.link_telegram_contact(telegram_id, chat_id, phone, pending_referral)
        if pending_referral:
            tg.update_telegram_session(telegram_id, pending_referral_code=None)
        bonus_note = " اعتبار هدیه فعال شد." if created and balance > 0 else ""
        await tg.send_telegram_message(chat_id, f"حساب تلگرام وصل شد.{bonus_note}")
        await tg.send_telegram_message(chat_id, tg.WELCOME_TEXT)
        return

    if not session.get("user_id"):
        await tg.send_telegram_message(
            chat_id,
            "برای تحلیل پیام در تلگرام، اول شماره موبایلت را تایید کن.",
            tg.contact_keyboard(),
        )
        return

    if not text:
        await tg.send_telegram_message(chat_id, "فعلاً فقط متن پیام را می‌توانم تحلیل کنم.")
        return

    sender_name, sender_id = tg.detect_forward_sender(message)
    await _analyze_message(chat_id, telegram_id, session, text, sender_name, sender_id)


# ============================================================
#  Core: forward → analysis card (NODES.decode1 / memory decode)
# ============================================================
def _same_sender(session: dict[str, Any], name: str | None, sid: str | None) -> bool:
    if sid and session.get("forward_from_id"):
        return sid == session.get("forward_from_id")
    if name and session.get("forward_from_name"):
        return name == session.get("forward_from_name")
    # Typed follow-up (no forward header) in an already-saved conversation.
    return name is None


async def _analyze_message(
    chat_id: str,
    telegram_id: str,
    session: dict[str, Any],
    text: str,
    sender_name: str | None,
    sender_id: str | None,
) -> None:
    await tg.send_chat_action(chat_id)
    user_id = str(session["user_id"])
    ghost = bool(session.get("ghost_mode"))

    contact_id: str | None = None
    memory = False
    if not ghost and session.get("memory_on") and session.get("contact_id") and _same_sender(session, sender_name, sender_id):
        contact_id = str(session["contact_id"])
        memory = True

    rel = session.get("relationship_type") or "unknown"
    goal = session.get("user_goal") or "understand_only"
    token = tg.create_session_token(user_id)
    payload = FreeDecodeIn(
        message_text=text,
        relationship_type=rel,
        user_goal=goal,
        privacy_consent=_CONSENT_TO_PRIVACY.get(session.get("consent") or "none", "none"),
        contact_id=contact_id,
        ghost_mode=ghost,
    )
    result = await create_free_decode(payload, authorization=f"Bearer {token}")

    effective_name = sender_name or session.get("forward_from_name")
    tg.update_telegram_session(
        telegram_id,
        state="awaiting_action",
        message_text=text,
        decode_id=result.decode_id,
        last_free_json=dumps(result.free_output.model_dump()) if result.free_output else None,
        forward_from_name=effective_name,
        forward_from_id=sender_id or session.get("forward_from_id"),
        contact_id=result.contact_id or contact_id,
    )

    if result.safety_output:
        safety = result.safety_output
        await tg.send_telegram_message(
            chat_id,
            f"⚠️ <b>{safety.warning_title}</b>\n\n{safety.priority}\n\n{safety.recommendation}",
        )
        return

    free_output = result.free_output
    if free_output is None:
        await tg.send_telegram_message(chat_id, "تحلیل ساخته نشد. دوباره امتحان کن.")
        return

    if effective_name and not memory:
        await tg.send_telegram_message(chat_id, f"این رو {effective_name} برات فرستاده. قبل از اینکه جواب بدی، بذار بخونمش 👇")

    card = tg.render_analysis_card(free_output.model_dump(), memory=memory, sender_name=effective_name)
    await tg.send_telegram_message(chat_id, card, tg.decode_keyboard(memory))

    # Information extraction (dates / phone) — NODES.decode2 behaviour.
    items = tg.extract_info(text, effective_name)
    if items:
        has_time = any(it["icon"] == "⏰" for it in items)
        await tg.send_telegram_message(
            chat_id,
            tg.render_info(items),
            tg.reminder_keyboard() if has_time else None,
        )


# ============================================================
#  Callback queries (inline keyboard = the interaction engine)
# ============================================================
async def _handle_callback(callback: dict[str, Any]) -> None:
    data = str(callback.get("data") or "")
    message = callback.get("message") or {}
    chat_id = str(message.get("chat", {}).get("id") or "")
    from_user = callback.get("from") or {}
    telegram_id = str(from_user.get("id") or "")
    if not chat_id or not telegram_id:
        return
    await tg.answer_callback(callback.get("id"))
    session = tg.get_or_create_telegram_session(telegram_id, chat_id)
    if not session.get("user_id"):
        await tg.send_telegram_message(chat_id, "اول شماره موبایل را تایید کن.", tg.contact_keyboard())
        return

    # --- refine: relationship → goal → deeper ---
    if data == "n:askrel":
        name = session.get("forward_from_name") or "این فرستنده"
        await tg.send_telegram_message(chat_id, f"با {name} چه نسبتی داری؟ این کمک می‌کنه لحن رو درست بسنجم.", tg.relationship_keyboard("rel"))
        return
    if data.startswith("rel:"):
        tg.update_telegram_session(telegram_id, relationship_type=data.removeprefix("rel:"))
        await tg.send_telegram_message(chat_id, "از این پاسخ چی می‌خوای؟", tg.goal_keyboard())
        return
    if data.startswith("goal:"):
        tg.update_telegram_session(telegram_id, user_goal=data.removeprefix("goal:"))
        await _run_deeper(chat_id, telegram_id, tg.get_or_create_telegram_session(telegram_id, chat_id))
        return

    # --- suggested replies + tone ---
    if data == "n:replies":
        await _run_replies(chat_id, telegram_id, session)
        return
    if data.startswith("tone:"):
        await _run_tone(chat_id, telegram_id, session, data.removeprefix("tone:"))
        return

    # --- translate / personality ---
    if data == "n:translate":
        await _run_translate(chat_id, session)
        return
    if data == "n:personality":
        await _run_personality(chat_id, session)
        return

    # --- save to contacts ---
    if data == "n:save":
        await _run_save_ask(chat_id, session)
        return
    if data == "save:yes":
        if session.get("relationship_type"):
            await _run_save_note(chat_id)
        else:
            await tg.send_telegram_message(chat_id, "نسبت‌تون چیه؟ (همینی که توی وب هم انتخاب می‌کنی)", tg.relationship_keyboard("srel"))
        return
    if data.startswith("srel:"):
        tg.update_telegram_session(telegram_id, relationship_type=data.removeprefix("srel:"))
        await _run_save_note(chat_id)
        return
    if data.startswith("note:"):
        await _run_save_done(chat_id, telegram_id, tg.get_or_create_telegram_session(telegram_id, chat_id), data.removeprefix("note:"))
        return
    if data == "save:later":
        await tg.send_telegram_message(
            chat_id,
            "باشه، ذخیره‌ش نکردم. این پیام رو با یه <b>شناسهٔ موقت و بی‌نام</b> نگه می‌دارم تا اگه نظرت عوض شد، تاریخچه‌ش نپره.",
            tg.save_later_keyboard(),
        )
        return

    # --- privacy / consent / ghost ---
    if data == "save:privacy":
        await tg.send_telegram_message(
            chat_id,
            "<b>کنترلِ داده‌ات</b> — مثلِ نسخهٔ وب:\n\n"
            "• <b>بله، بدونِ نام</b> — برای بهبودِ مدل، بی‌هویت\n"
            "• <b>ذخیره در تاریخچهٔ من</b> — فقط برای خودت\n"
            "• <b>فقط پردازش، بدونِ ذخیره</b>\n\n"
            "👻 <b>حالتِ شبح:</b> تحلیل و پاسخ در تاریخچه ذخیره نمی‌شه.",
            tg.privacy_keyboard(),
        )
        return
    if data.startswith("pc:"):
        tg.update_telegram_session(telegram_id, consent=data.removeprefix("pc:"))
        await tg.send_telegram_message(chat_id, "ثبت شد ✅ همین تنظیم توی وب هم اعمال می‌شه.", tg.privacy_set_keyboard())
        return
    if data == "n:ghost":
        tg.update_telegram_session(telegram_id, ghost_mode=1)
        await tg.send_telegram_message(chat_id, "👻 حالتِ شبح روشن شد. از این لحظه، نه تحلیل و نه پاسخ در تاریخچه نمی‌مونه. هر وقت خواستی با /cancel خاموشش کن.")
        return

    # --- reminder / next forward / web ---
    if data == "n:reminder":
        await _run_reminder(chat_id, telegram_id, session)
        return
    if data == "n:nextforward":
        name = session.get("forward_from_name") or "همون فرد"
        await tg.send_telegram_message(chat_id, f"عالی! حالا یه پیامِ دیگه از {name} برام فوروارد کن تا این‌بار با حافظهٔ رابطه بخونمش.")
        return

    # --- legacy paid / payment paths (kept for credit flow) ---
    if data.startswith("paid:"):
        await _run_paid_decode(chat_id, str(session["user_id"]), data.removeprefix("paid:"))
        return
    if data.startswith("buy:"):
        await _send_payment(chat_id, str(session["user_id"]), data.removeprefix("buy:") or "credits_5")
        return


async def _run_deeper(chat_id: str, telegram_id: str, session: dict[str, Any]) -> None:
    await tg.send_chat_action(chat_id)
    message_text = str(session.get("message_text") or "")
    if not message_text:
        await tg.send_telegram_message(chat_id, "پیامی برای تحلیل پیدا نکردم. دوباره یه پیام فوروارد کن.")
        return
    user_id = str(session["user_id"])
    ghost = bool(session.get("ghost_mode"))
    rel = session.get("relationship_type") or "unknown"
    goal = session.get("user_goal") or "understand_only"
    token = tg.create_session_token(user_id)
    payload = FreeDecodeIn(
        message_text=message_text,
        relationship_type=rel,
        user_goal=goal,
        privacy_consent=_CONSENT_TO_PRIVACY.get(session.get("consent") or "none", "none"),
        contact_id=str(session["contact_id"]) if session.get("contact_id") and session.get("memory_on") else None,
        ghost_mode=ghost,
    )
    result = await create_free_decode(payload, authorization=f"Bearer {token}")
    if result.free_output is None:
        await tg.send_telegram_message(chat_id, "تحلیل عمیق‌تر ساخته نشد. دوباره امتحان کن.")
        return
    free = result.free_output
    tg.update_telegram_session(
        telegram_id,
        decode_id=result.decode_id,
        last_free_json=dumps(free.model_dump()),
    )
    goal_label = tg.GOAL_LABELS.get(goal, goal)
    await tg.send_telegram_message(
        chat_id,
        f"با این که هدفت «{goal_label}»ـه، این رو بدون:\n\n{free.likely_underlying_need}",
    )
    await tg.send_telegram_message(
        chat_id,
        f"⚠️ <b>چه‌کاری نکن:</b> {free.conversation_risk}\n\n✅ <b>مسیرِ بهتر:</b> {free.recommended_direction}",
        tg.deeper_keyboard(),
    )


async def _run_replies(chat_id: str, telegram_id: str, session: dict[str, Any]) -> None:
    await tg.send_chat_action(chat_id)
    user_id = str(session["user_id"])
    ghost = bool(session.get("ghost_mode"))
    saved = bool(session.get("memory_on"))
    try:
        if ghost:
            raw = session.get("last_free_json")
            if not raw:
                await tg.send_telegram_message(chat_id, "اول یه پیام بفرست تا تحلیلش کنم، بعد جواب می‌سازم.")
                return
            free = FreeDecodeOutput.model_validate(loads(raw))
            result = await create_ghost_paid_decode(
                GhostPaidDecodeIn(
                    decode_id=str(session.get("decode_id") or "ghost"),
                    free_output=free,
                    message_text=str(session.get("message_text") or ""),
                    relationship_type=session.get("relationship_type") or "unknown",
                    user_goal=session.get("user_goal") or "understand_only",
                ),
                user_id=user_id,
            )
        else:
            decode_id = session.get("decode_id")
            if not decode_id:
                await tg.send_telegram_message(chat_id, "اول یه پیام بفرست تا تحلیلش کنم، بعد جواب می‌سازم.")
                return
            result = await create_paid_decode(PaidDecodeIn(decode_id=str(decode_id)), user_id=user_id)
    except HTTPException as exc:
        if exc.status_code == 402:
            await _send_payment(chat_id, user_id, "credits_5")
            return
        if exc.status_code == 503:
            await tg.send_telegram_message(chat_id, str(exc.detail))
            return
        raise

    output = result.paid_output
    base_reply = output.reply_options[0].text if output.reply_options else output.copy_ready_reply
    tg.update_telegram_session(telegram_id, last_reply_text=base_reply)

    await tg.send_telegram_message(chat_id, "سه جور می‌تونی جواب بدی — هر سه دلخوری رو می‌بینن؛ فرقشون توی قاطعیته. روی متنِ هر جواب نگه‌داری، کپی می‌شه.")
    for opt in output.reply_options:
        risk = ""
        if opt.reaction_forecast:
            risk = f"  · ریسکِ {opt.reaction_forecast.risk_level}"
        await tg.send_telegram_message(
            chat_id,
            f"💬 <b>{opt.label}</b>{risk}\n\n<code>{tg._esc(opt.text)}</code>\n\n<i>چرا؟ {opt.why_it_works}</i>",
        )
    await tg.send_telegram_message(
        chat_id,
        f"اعتبار باقی‌مانده: {tg.fa_num(result.credit_balance)}\n\nمی‌خوای لحنش رو عوض کنم؟",
        tg.tone_keyboard(saved),
    )


async def _run_tone(chat_id: str, telegram_id: str, session: dict[str, Any], target: str) -> None:
    from app.services.ai import tone_edit

    base = session.get("last_reply_text")
    if not base:
        await tg.send_telegram_message(chat_id, "اول «جواب پیشنهادی» رو بزن تا یه متن داشته باشیم، بعد لحنش رو عوض می‌کنم.")
        return
    if target not in TONE_FA:
        return
    await tg.send_chat_action(chat_id)
    text = await tone_edit(
        base,
        target,
        session.get("relationship_type") or "unknown",
        session.get("user_goal") or "understand_only",
        session.get("message_text"),
    )
    tg.update_telegram_session(telegram_id, last_reply_text=text)
    await tg.send_telegram_message(
        chat_id,
        f"<b>نسخهٔ {TONE_FA[target]}:</b>\n\n<code>{tg._esc(text)}</code>",
        tg.tone_keyboard(bool(session.get("memory_on"))),
    )


async def _run_translate(chat_id: str, session: dict[str, Any]) -> None:
    raw = session.get("last_free_json")
    if not raw:
        await tg.send_telegram_message(chat_id, "اول یه پیام بفرست تا زیرمتنش رو ترجمه کنم.")
        return
    free = loads(raw)
    insight = free.get("insight_line") or free.get("dominant_lens_explanation") or "—"
    need = free.get("likely_underlying_need") or "—"
    alt = free.get("alternative_read") or "—"
    await tg.send_telegram_message(
        chat_id,
        "<b>🔍 ترجمهٔ زیرمتن — به زبانِ ساده:</b>\n\n"
        f"{insight}\n\n"
        f"<b>یعنی احتمالاً:</b> {need}\n\n"
        f"<b>برداشتِ دیگه:</b> {alt}",
        tg.translate_keyboard(),
    )


async def _run_personality(chat_id: str, session: dict[str, Any]) -> None:
    memory = bool(session.get("memory_on")) and bool(session.get("contact_id"))
    if memory:
        name, summary = tg.get_contact_memory_summary(str(session["user_id"]), str(session["contact_id"]))
        if summary:
            await tg.send_telegram_message(
                chat_id,
                f"<b>{name or 'این مخاطب'} — تصویرِ رابطه</b>\n\n{summary}",
                tg.personality_keyboard(True),
            )
            return
    raw = session.get("last_free_json")
    alt = loads(raw).get("alternative_read") if raw else None
    name = session.get("forward_from_name") or "این فرد"
    await tg.send_telegram_message(
        chat_id,
        f"<b>یه برداشتِ اولیه از {name}</b> (فقط از همین پیام):\n\n"
        f"{alt or 'هنوز برای یه تصویرِ دقیق، داده کافی ندارم.'}\n\n"
        "برای دقیق‌تر شدن، اگه ذخیره‌ش کنی، از روی الگوی پیام‌هاش تصویرِ واقعی‌تری بهت می‌دم.",
        tg.personality_keyboard(False),
    )


async def _run_save_ask(chat_id: str, session: dict[str, Any]) -> None:
    name = session.get("forward_from_name") or "این فرستنده"
    await tg.send_telegram_message(
        chat_id,
        f"این پیام از <b>{name}</b> فورواردشده و شناسه‌ش رو دارم. می‌خوای به مخاطب‌هات اضافه‌ش کنم؟\n\n"
        "<b>اگه اضافه کنی:</b> هر پیامی ازش فوروارد کنی، با کلِ تاریخچهٔ رابطه می‌خونمش — نه تنها و بی‌زمینه.\n"
        "<b>اگه نکنی:</b> با یه شناسهٔ موقت نگه‌ش می‌دارم تا تاریخچه از دست نره، ولی بدونِ نام.",
        tg.save_ask_keyboard(),
    )


async def _run_save_note(chat_id: str) -> None:
    await tg.send_telegram_message(
        chat_id,
        "یه یادداشتِ کوتاه دربارهٔ این رابطه؟ بعداً موقعِ تحلیل کمک می‌کنه. (اختیاری)",
        tg.save_note_keyboard(),
    )


async def _run_save_done(chat_id: str, telegram_id: str, session: dict[str, Any], note_key: str) -> None:
    note = tg.SAVE_NOTE_TEXTS.get(note_key, "—")
    name = session.get("forward_from_name") or "مخاطب"
    rel = session.get("relationship_type") or "unknown"
    contact_id = tg.upsert_contact_from_telegram(str(session["user_id"]), name, rel, note)
    tg.update_telegram_session(telegram_id, contact_id=contact_id, memory_on=1, pending_note=note)
    rel_label = tg.RELATIONSHIP_LABELS.get(rel, rel)
    await tg.send_telegram_message(chat_id, f"✅ {name} به مخاطب‌های تو اضافه شد")
    await tg.send_telegram_message(
        chat_id,
        f"👤 <b>{name}</b>\n"
        "✅ در مخاطب‌های تو ذخیره شد\n\n"
        f"نسبت: {rel_label}\n"
        f"یادداشتِ تو: {note}\n"
        "حافظهٔ رابطه: <b>فعال</b>\n\n"
        "🔄 این مخاطب توی نسخهٔ وب هم هست — همان نام، نسبت و یادداشت، همگام.\n\n"
        "تمومه ✅ از این به بعد هر پیامی ازش بیاد، با حافظهٔ رابطه تحلیلش می‌کنم.",
        tg.save_done_keyboard(),
    )


async def _run_reminder(chat_id: str, telegram_id: str, session: dict[str, Any]) -> None:
    message_text = str(session.get("message_text") or "")
    name = session.get("forward_from_name")
    items = tg.extract_info(message_text, name)
    notes = []
    phone_item = next((it for it in items if it["icon"] == "☎️"), None)
    time_item = next((it for it in items if it["icon"] == "⏰"), None)
    if phone_item and session.get("contact_id"):
        # Real action: persist the new number into the contact's profile note.
        tg.append_contact_note(str(session["user_id"]), str(session["contact_id"]), f"شماره: {phone_item['value']}")
        notes.append("☎️ شماره ذخیره شد")
    if time_item:
        notes.append(f"⏰ یادداشت شد: {time_item['value']}")
    head = " · ".join(notes) if notes else "یادداشت شد"
    await tg.send_telegram_message(
        chat_id,
        f"{head}\n\nانجام شد. این مورد رو برات نگه داشتم تا موقعِ جواب دادن یادت بمونه.",
    )


# ---- legacy paid + payment (credit flow preserved) ----
async def _run_paid_decode(chat_id: str, user_id: str, decode_id: str) -> None:
    try:
        result = await create_paid_decode(PaidDecodeIn(decode_id=decode_id), user_id=user_id)
    except HTTPException as exc:
        if exc.status_code == 402:
            await _send_payment(chat_id, user_id, "credits_5")
            return
        raise
    output = result.paid_output
    replies = "\n\n".join(
        f"<b>{item.label}</b>\n{item.text}\nواکنش محتمل: {item.reaction_prediction or 'نامشخص'}"
        for item in output.reply_options
    )
    await tg.send_telegram_message(
        chat_id,
        f"🔓 <b>پاسخ‌های قابل ارسال</b>\n\n{replies}\n\nاعتبار باقی‌مانده: {tg.fa_num(result.credit_balance)}",
    )


async def _send_payment(chat_id: str, user_id: str, package_id: str) -> None:
    payment = create_payment(user_id, package_id if package_id in {"credits_5", "credits_20", "credits_50"} else "credits_5")
    await tg.send_telegram_message(
        chat_id,
        "برای ساخت پاسخ قابل ارسال، اعتبارت را شارژ کن.",
        tg.buy_keyboard(payment["payment_url"]),
    )
