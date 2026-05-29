from __future__ import annotations

from typing import Any

from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.schemas import FreeDecodeIn, PaidDecodeIn
from app.routers.decode import create_free_decode, create_paid_decode
from app.services.payments import create_payment
from app.services import telegram as tg

router = APIRouter(prefix="/telegram", tags=["telegram"])


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
        if session.get("user_id"):
            await tg.send_telegram_message(chat_id, "پیامت را بفرست تا سریع تحلیلش کنم.")
        else:
            await tg.send_telegram_message(
                chat_id,
                "به Message Decoder خوش آمدی. برای شروع، شماره موبایلت را با دکمه زیر تایید کن.",
                tg.contact_keyboard(),
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
        await tg.send_telegram_message(chat_id, "حالت Ghost برای پیام بعدی روشن شد. متن را بفرست؛ ذخیره نمی‌شود و پاسخ پولی روی آن فعال نیست.")
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
        _, balance, created = tg.link_telegram_contact(telegram_id, chat_id, phone)
        bonus_note = " اعتبار هدیه فعال شد." if created and balance > 0 else ""
        await tg.send_telegram_message(chat_id, f"حساب تلگرام وصل شد.{bonus_note}\nحالا پیام را بفرست.")
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

    tg.update_telegram_session(
        telegram_id,
        state="awaiting_relationship",
        message_text=text,
        relationship_type=None,
        user_goal=None,
        decode_id=None,
    )
    await tg.send_telegram_message(chat_id, "این پیام مربوط به کدام رابطه است؟", tg.relationship_keyboard())


async def _handle_callback(callback: dict[str, Any]) -> None:
    data = str(callback.get("data") or "")
    message = callback.get("message") or {}
    chat_id = str(message.get("chat", {}).get("id") or "")
    from_user = callback.get("from") or {}
    telegram_id = str(from_user.get("id") or "")
    if not chat_id or not telegram_id:
        return
    session = tg.get_or_create_telegram_session(telegram_id, chat_id)
    if not session.get("user_id"):
        await tg.send_telegram_message(chat_id, "اول شماره موبایل را تایید کن.", tg.contact_keyboard())
        return

    if data.startswith("rel:"):
        relationship = data.removeprefix("rel:")
        tg.update_telegram_session(telegram_id, relationship_type=relationship, state="awaiting_goal")
        await tg.send_telegram_message(chat_id, "هدفت از پاسخ دادن چیست؟", tg.goal_keyboard())
        return

    if data.startswith("goal:"):
        goal = data.removeprefix("goal:")
        await _run_free_decode(chat_id, telegram_id, session, goal)
        return

    if data.startswith("paid:"):
        await _run_paid_decode(chat_id, str(session["user_id"]), data.removeprefix("paid:"))
        return

    if data.startswith("buy:"):
        await _send_payment(chat_id, str(session["user_id"]), data.removeprefix("buy:") or "credits_5")
        return


async def _run_free_decode(chat_id: str, telegram_id: str, session: dict[str, Any], goal: str) -> None:
    message_text = str(session.get("message_text") or "")
    relationship_type = str(session.get("relationship_type") or "unknown")
    if not message_text:
        await tg.send_telegram_message(chat_id, "پیامی برای تحلیل پیدا نکردم. لطفاً متن را دوباره بفرست.")
        return
    user_id = str(session["user_id"])
    ghost_mode = bool(session.get("ghost_mode"))
    token = tg.create_session_token(user_id)
    payload = FreeDecodeIn(
        message_text=message_text,
        relationship_type=relationship_type,
        user_goal=goal,
        privacy_consent="none",
        ghost_mode=ghost_mode,
    )
    result = await create_free_decode(payload, authorization=f"Bearer {token}")
    tg.update_telegram_session(
        telegram_id,
        state="awaiting_message",
        user_goal=goal,
        decode_id=result.decode_id,
        ghost_mode=0,
    )
    if result.safety_output:
        safety = result.safety_output
        await tg.send_telegram_message(
            chat_id,
            f"⚠️ <b>{safety.warning_title}</b>\n\n{safety.recommendation}\n\n{safety.suggested_reply}",
        )
        return
    output = result.free_output
    if output is None:
        await tg.send_telegram_message(chat_id, "تحلیل ساخته نشد. دوباره امتحان کن.")
        return
    mix = output.lens_mix
    text = (
        f"📊 <b>تحلیل سریع</b>\n"
        f"لنز غالب: {output.dominant_lens.fa}\n"
        f"سهم لنزها: Dopamine {mix.dopamine}% | Oxytocin {mix.oxytocin}% | Serotonin {mix.serotonin}%\n"
        f"شدت لحن: {output.tone_stress.label} ({output.tone_stress.intensity}/100)\n\n"
        f"⚠️ ریسک مکالمه: {output.conversation_risk}\n"
        f"💡 برداشت احتمالی: {output.likely_underlying_need}\n"
        f"🧭 مسیر پیشنهادی: {output.recommended_direction}"
    )
    if ghost_mode:
        text += "\n\nGhost Mode روشن بود؛ این تحلیل ذخیره نشد و پاسخ پولی برای آن فعال نیست."
        await tg.send_telegram_message(chat_id, text)
        return
    await tg.send_telegram_message(chat_id, text, tg.paid_keyboard(result.decode_id))


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
        f"🔓 <b>پاسخ‌های قابل ارسال</b>\n\n{replies}\n\nاعتبار باقی‌مانده: {result.credit_balance}",
    )


async def _send_payment(chat_id: str, user_id: str, package_id: str) -> None:
    payment = create_payment(user_id, package_id if package_id in {"credits_5", "credits_20", "credits_50"} else "credits_5")
    await tg.send_telegram_message(
        chat_id,
        "برای ساخت پاسخ قابل ارسال، اعتبارت را شارژ کن.",
        tg.buy_keyboard(payment["payment_url"]),
    )
