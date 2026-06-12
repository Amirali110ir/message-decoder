from __future__ import annotations

import hashlib
import hmac
import json
import logging
import secrets
from datetime import datetime, timedelta, timezone

from fastapi import Header, HTTPException
import httpx

from app.config import Settings
from app.database import db
from app.utils import new_id, now_iso

logger = logging.getLogger("message_decoder.auth")


PROVIDER_ERROR_FA = {
    "smsir": {
        "missing_api_key": "کلید API سرویس پیامک تنظیم نشده است.",
        "missing_template": "قالب پیامک تایید تنظیم نشده است.",
        "missing_line": "خط ارسال پیامک تنظیم نشده است.",
        "network": "اتصال به سرویس پیامک برقرار نشد.",
        "invalid": "پاسخ سرویس پیامک نامعتبر بود.",
        "rejected": "ارسال پیامک از طرف سرویس رد شد.",
    },
    "kavenegar": {
        "missing_api_key": "کلید API سرویس پیامک تنظیم نشده است.",
        "missing_template": "قالب پیامک تایید تنظیم نشده است.",
        "missing_sender": "خط ارسال پیامک تنظیم نشده است.",
        "network": "اتصال به سرویس پیامک برقرار نشد.",
        "invalid": "پاسخ سرویس پیامک نامعتبر بود.",
        "rejected": "ارسال پیامک از طرف سرویس رد شد.",
    },
}


def _fa(provider: str, key: str, default: str = "ارسال پیامک با خطا مواجه شد.") -> str:
    return PROVIDER_ERROR_FA.get(provider, {}).get(key, default)


def _unescape_template(template: str) -> str:
    return template.replace("\\n", "\n").replace("\\t", "\t")


def normalize_digits(value: str) -> str:
    persian_to_english = str.maketrans("۰۱۲۳۴۵۶۷۸۹", "0123456789")
    digits = "".join(ch for ch in value.translate(persian_to_english).strip() if ch.isdigit())
    if digits.startswith("0098"):
        digits = digits[2:]
    if digits.startswith("98") and len(digits) == 12:
        return "0" + digits[2:]
    if digits.startswith("9") and len(digits) == 10:
        return "0" + digits
    return digits


def generate_otp_code() -> str:
    return f"{secrets.randbelow(1_000_000):06d}"


def _utc_now() -> datetime:
    return datetime.now(timezone.utc)


def _parse_iso(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        parsed = datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed


def create_or_update_otp(phone: str, code: str, ttl_seconds: int) -> None:
    created_at = _utc_now()
    expires_at = created_at + timedelta(seconds=ttl_seconds)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO auth_otps (phone, code, created_at, expires_at, attempts, consumed_at)
            VALUES (?, ?, ?, ?, 0, NULL)
            ON CONFLICT(phone) DO UPDATE SET
                code = excluded.code,
                created_at = excluded.created_at,
                expires_at = excluded.expires_at,
                attempts = 0,
                consumed_at = NULL
            """,
            (normalize_digits(phone), code, created_at.isoformat(), expires_at.isoformat()),
        )


def record_sms_send_log(
    *,
    provider: str,
    purpose: str,
    phone: str,
    status: str,
    template_id: str | None = None,
    message_id: str | None = None,
    request_payload: dict | None = None,
    response_payload: dict | None = None,
    error_message: str | None = None,
) -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO sms_send_logs (
                id, provider, purpose, phone, template_id, message_id, status,
                request_payload, response_payload, error_message, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("sms"),
                provider,
                purpose,
                normalize_digits(phone),
                template_id,
                message_id,
                status,
                json.dumps(request_payload, ensure_ascii=False) if request_payload is not None else None,
                json.dumps(response_payload, ensure_ascii=False) if response_payload is not None else None,
                error_message,
                now_iso(),
            ),
        )


def extract_smsir_message_id(body: dict) -> str | None:
    data = body.get("data")
    if isinstance(data, dict):
        for key in ("messageId", "message_id", "id"):
            value = data.get(key)
            if value is not None:
                return str(value)
        message_ids = data.get("messageIds")
        if isinstance(message_ids, list) and message_ids:
            return str(message_ids[0])
    return None


def extract_kavenegar_message_id(body: dict) -> str | None:
    entries = body.get("entries")
    if isinstance(entries, list) and entries:
        entry = entries[0]
        if isinstance(entry, dict):
            value = entry.get("messageid") or entry.get("message_id")
            if value is not None:
                return str(value)
    return None


def send_kavenegar_lookup_otp(phone: str, code: str, settings: Settings) -> None:
    if not settings.kavenegar_api_key:
        logger.error("kavenegar.lookup missing_api_key")
        raise HTTPException(status_code=500, detail=_fa("kavenegar", "missing_api_key"))
    if not settings.kavenegar_template:
        logger.error("kavenegar.lookup missing_template")
        raise HTTPException(status_code=500, detail=_fa("kavenegar", "missing_template"))

    base_url = settings.kavenegar_api_base_url.rstrip("/")
    url = f"{base_url}/v1/{settings.kavenegar_api_key}/verify/lookup.json"
    payload = {
        "receptor": normalize_digits(phone),
        "token": code,
        "template": settings.kavenegar_template,
        "type": settings.kavenegar_type,
    }

    try:
        response = httpx.post(url, data=payload, timeout=10)
        body = response.json()
    except httpx.RequestError as exc:
        record_sms_send_log(
            provider="kavenegar",
            purpose="otp",
            phone=phone,
            template_id=settings.kavenegar_template,
            status="failed",
            request_payload=payload,
            error_message=str(exc),
        )
        logger.error("kavenegar.lookup network_error phone=%s err=%s", _mask_phone(phone), exc)
        raise HTTPException(status_code=502, detail=_fa("kavenegar", "network")) from exc
    except ValueError as exc:
        record_sms_send_log(
            provider="kavenegar",
            purpose="otp",
            phone=phone,
            template_id=settings.kavenegar_template,
            status="failed",
            request_payload=payload,
            error_message="Kavenegar returned an invalid response",
        )
        logger.error("kavenegar.lookup invalid_response phone=%s", _mask_phone(phone))
        raise HTTPException(status_code=502, detail=_fa("kavenegar", "invalid")) from exc

    status = body.get("return", {}).get("status")
    ok = status == 200
    record_sms_send_log(
        provider="kavenegar",
        purpose="otp",
        phone=phone,
        template_id=settings.kavenegar_template,
        message_id=extract_kavenegar_message_id(body),
        status="sent" if ok else "failed",
        request_payload=payload,
        response_payload=body,
        error_message=None if ok else str(body.get("return", {}).get("message") or "Kavenegar OTP request was rejected"),
    )
    if status != 200:
        logger.error("kavenegar.lookup rejected phone=%s status=%s body=%s", _mask_phone(phone), status, body)
        raise HTTPException(status_code=502, detail=_fa("kavenegar", "rejected"))


def send_kavenegar_sms_otp(phone: str, code: str, settings: Settings) -> None:
    if not settings.kavenegar_api_key:
        logger.error("kavenegar.sms missing_api_key")
        raise HTTPException(status_code=500, detail=_fa("kavenegar", "missing_api_key"))
    if not settings.kavenegar_sender:
        logger.error("kavenegar.sms missing_sender")
        raise HTTPException(status_code=500, detail=_fa("kavenegar", "missing_sender"))

    base_url = settings.kavenegar_api_base_url.rstrip("/")
    url = f"{base_url}/v1/{settings.kavenegar_api_key}/sms/send.json"
    payload = {
        "receptor": normalize_digits(phone),
        "sender": settings.kavenegar_sender,
        "message": format_otp_login_message(code, settings),
    }

    try:
        response = httpx.post(url, data=payload, timeout=10)
        body = response.json()
    except httpx.RequestError as exc:
        record_sms_send_log(
            provider="kavenegar",
            purpose="otp",
            phone=phone,
            status="failed",
            request_payload=payload,
            error_message=str(exc),
        )
        logger.error("kavenegar.sms network_error phone=%s err=%s", _mask_phone(phone), exc)
        raise HTTPException(status_code=502, detail=_fa("kavenegar", "network")) from exc
    except ValueError as exc:
        record_sms_send_log(
            provider="kavenegar",
            purpose="otp",
            phone=phone,
            status="failed",
            request_payload=payload,
            error_message="Kavenegar returned an invalid response",
        )
        logger.error("kavenegar.sms invalid_response phone=%s", _mask_phone(phone))
        raise HTTPException(status_code=502, detail=_fa("kavenegar", "invalid")) from exc

    status = body.get("return", {}).get("status")
    ok = status == 200
    record_sms_send_log(
        provider="kavenegar",
        purpose="otp",
        phone=phone,
        message_id=extract_kavenegar_message_id(body),
        status="sent" if ok else "failed",
        request_payload=payload,
        response_payload=body,
        error_message=None if ok else str(body.get("return", {}).get("message") or "Kavenegar SMS request was rejected"),
    )
    if status != 200:
        logger.error("kavenegar.sms rejected phone=%s status=%s body=%s", _mask_phone(phone), status, body)
        raise HTTPException(status_code=502, detail=_fa("kavenegar", "rejected"))


def send_kavenegar_otp(phone: str, code: str, settings: Settings) -> None:
    method = settings.kavenegar_method.lower()
    if method in ("verify_lookup", "lookup", "verify"):
        send_kavenegar_lookup_otp(phone, code, settings)
        return
    if method in ("send", "sms_send", "sms"):
        send_kavenegar_sms_otp(phone, code, settings)
        return
    raise HTTPException(status_code=500, detail=f"Unsupported Kavenegar method: {settings.kavenegar_method}")


def send_smsir_verify_otp(phone: str, code: str, settings: Settings) -> None:
    if not settings.smsir_api_key:
        logger.error("smsir.verify missing_api_key")
        raise HTTPException(status_code=500, detail=_fa("smsir", "missing_api_key"))
    if not settings.smsir_template_id:
        logger.error("smsir.verify missing_template")
        raise HTTPException(status_code=500, detail=_fa("smsir", "missing_template"))

    normalized_phone = normalize_digits(phone)
    template_id = settings.smsir_template_id.strip()
    try:
        parsed_template_id: int | str = int(template_id)
    except ValueError:
        parsed_template_id = template_id

    base_url = settings.smsir_api_base_url.rstrip("/")
    url = f"{base_url}/v1/send/verify"
    payload = {
        "mobile": normalized_phone,
        "templateId": parsed_template_id,
        "parameters": [
            {
                "name": settings.smsir_parameter_name,
                "value": code,
            }
        ],
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": settings.smsir_api_key,
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=10)
        body = response.json()
    except httpx.RequestError as exc:
        record_sms_send_log(
            provider="smsir",
            purpose="otp",
            phone=normalized_phone,
            template_id=template_id,
            status="failed",
            request_payload=payload,
            error_message=str(exc),
        )
        logger.error("smsir.verify network_error phone=%s err=%s", _mask_phone(normalized_phone), exc)
        raise HTTPException(status_code=502, detail=_fa("smsir", "network")) from exc
    except ValueError as exc:
        record_sms_send_log(
            provider="smsir",
            purpose="otp",
            phone=normalized_phone,
            template_id=template_id,
            status="failed",
            request_payload=payload,
            error_message="SMS.ir returned an invalid response",
        )
        logger.error("smsir.verify invalid_response phone=%s", _mask_phone(normalized_phone))
        raise HTTPException(status_code=502, detail=_fa("smsir", "invalid")) from exc

    ok = response.status_code < 400 and body.get("status") in (1, "1", 200, "200", True)
    message_id = extract_smsir_message_id(body)
    record_sms_send_log(
        provider="smsir",
        purpose="otp",
        phone=normalized_phone,
        template_id=template_id,
        message_id=message_id,
        status="sent" if ok else "failed",
        request_payload=payload,
        response_payload=body,
        error_message=None if ok else str(body.get("message") or "SMS.ir OTP request was rejected"),
    )
    if not ok:
        logger.error("smsir.verify rejected phone=%s status=%s body=%s", _mask_phone(normalized_phone), response.status_code, body)
        raise HTTPException(status_code=502, detail=_fa("smsir", "rejected"))


def send_smsir_bulk_otp(phone: str, code: str, settings: Settings) -> None:
    if not settings.smsir_api_key:
        logger.error("smsir.bulk missing_api_key")
        raise HTTPException(status_code=500, detail=_fa("smsir", "missing_api_key"))
    if not settings.smsir_line_number:
        logger.error("smsir.bulk missing_line")
        raise HTTPException(status_code=500, detail=_fa("smsir", "missing_line"))

    normalized_phone = normalize_digits(phone)
    line_number = settings.smsir_line_number.strip()
    try:
        parsed_line_number: int | str = int(line_number)
    except ValueError:
        parsed_line_number = line_number

    base_url = settings.smsir_api_base_url.rstrip("/")
    url = f"{base_url}/v1/send/bulk"
    payload = {
        "lineNumber": parsed_line_number,
        "messageText": format_otp_login_message(code, settings),
        "mobiles": [normalized_phone],
        "sendDateTime": None,
    }
    headers = {
        "Accept": "application/json",
        "Content-Type": "application/json",
        "x-api-key": settings.smsir_api_key,
    }

    try:
        response = httpx.post(url, json=payload, headers=headers, timeout=10)
        body = response.json()
    except httpx.RequestError as exc:
        record_sms_send_log(
            provider="smsir",
            purpose="otp",
            phone=normalized_phone,
            status="failed",
            request_payload=payload,
            error_message=str(exc),
        )
        logger.error("smsir.bulk network_error phone=%s err=%s", _mask_phone(normalized_phone), exc)
        raise HTTPException(status_code=502, detail=_fa("smsir", "network")) from exc
    except ValueError as exc:
        record_sms_send_log(
            provider="smsir",
            purpose="otp",
            phone=normalized_phone,
            status="failed",
            request_payload=payload,
            error_message="SMS.ir returned an invalid response",
        )
        logger.error("smsir.bulk invalid_response phone=%s", _mask_phone(normalized_phone))
        raise HTTPException(status_code=502, detail=_fa("smsir", "invalid")) from exc

    ok = response.status_code < 400 and body.get("status") in (1, "1", 200, "200", True)
    message_id = extract_smsir_message_id(body)
    record_sms_send_log(
        provider="smsir",
        purpose="otp",
        phone=normalized_phone,
        message_id=message_id,
        status="sent" if ok else "failed",
        request_payload=payload,
        response_payload=body,
        error_message=None if ok else str(body.get("message") or "SMS.ir OTP request was rejected"),
    )
    if not ok:
        logger.error("smsir.bulk rejected phone=%s status=%s body=%s", _mask_phone(normalized_phone), response.status_code, body)
        raise HTTPException(status_code=502, detail=_fa("smsir", "rejected"))


def send_smsir_otp(phone: str, code: str, settings: Settings) -> None:
    method = settings.smsir_method.lower()
    if method == "auto":
        method = "verify" if settings.smsir_template_id else "bulk"
    if method in ("verify", "send_verify", "template"):
        send_smsir_verify_otp(phone, code, settings)
        return
    if method in ("bulk", "send", "sms"):
        send_smsir_bulk_otp(phone, code, settings)
        return
    raise HTTPException(status_code=500, detail=f"Unsupported SMS.ir method: {settings.smsir_method}")


OTP_RESEND_COOLDOWN_SECONDS = 60


def _check_otp_cooldown(phone: str) -> None:
    """Reject if an OTP was already sent to this phone within the cooldown window."""
    with db() as conn:
        row = conn.execute(
            "SELECT created_at FROM auth_otps WHERE phone = ? AND consumed_at IS NULL",
            (phone,),
        ).fetchone()
    if not row:
        return
    last_sent = _parse_iso(row["created_at"])
    if last_sent and (_utc_now() - last_sent).total_seconds() < OTP_RESEND_COOLDOWN_SECONDS:
        raise HTTPException(
            status_code=429,
            detail=f"کد قبلی هنوز معتبر است. لطفاً {OTP_RESEND_COOLDOWN_SECONDS} ثانیه صبر کنید.",
        )


def request_otp_code(phone: str, settings: Settings) -> tuple[str | None, dict | None]:
    provider = settings.otp_provider.lower()
    code = normalize_digits(settings.dev_otp_code) if provider == "mock" else generate_otp_code()
    normalized_phone = normalize_digits(phone)

    logger.info("otp.request provider=%s phone=%s production=%s", provider, _mask_phone(normalized_phone), settings.is_production)

    if provider != "mock":
        _check_otp_cooldown(normalized_phone)

    telegram_payload = None
    if provider != "mock":
        telegram_payload = create_telegram_payload_if_linked(normalized_phone, code, settings)

    if provider == "mock":
        create_or_update_otp(normalized_phone, code, settings.otp_ttl_seconds)
        expose_code = None if settings.is_production else code
        logger.info("otp.mock saved phone=%s expose_code=%s", _mask_phone(normalized_phone), bool(expose_code))
        return expose_code, None
    if provider == "kavenegar":
        send_kavenegar_otp(normalized_phone, code, settings)
        create_or_update_otp(normalized_phone, code, settings.otp_ttl_seconds)
        logger.info("otp.kavenegar sent phone=%s telegram_paired=%s", _mask_phone(normalized_phone), bool(telegram_payload))
        return None, telegram_payload
    if provider in ("smsir", "sms.ir"):
        send_smsir_otp(normalized_phone, code, settings)
        create_or_update_otp(normalized_phone, code, settings.otp_ttl_seconds)
        logger.info("otp.smsir sent phone=%s telegram_paired=%s", _mask_phone(normalized_phone), bool(telegram_payload))
        return None, telegram_payload

    logger.error("otp.unsupported_provider provider=%s", provider)
    raise HTTPException(status_code=500, detail=f"Unsupported OTP provider: {settings.otp_provider}")


def _mask_phone(phone: str) -> str:
    if not phone or len(phone) < 4:
        return "***"
    return f"{phone[:3]}***{phone[-2:]}"


def create_telegram_payload_if_linked(phone: str, code: str, settings: Settings) -> dict | None:
    if not settings.telegram_bridge_secret:
        logger.info("telegram_otp.skipped reason=bridge_secret_missing phone=%s", _mask_phone(phone))
        return None
    with db() as conn:
        user = conn.execute("SELECT telegram_id FROM users WHERE phone = ?", (phone,)).fetchone()
    if not user or not user["telegram_id"]:
        logger.info("telegram_otp.skipped reason=user_not_linked phone=%s", _mask_phone(phone))
        return None

    logger.info("telegram_otp.payload_ready phone=%s", _mask_phone(phone))
    chat_id = str(user["telegram_id"])
    text = f"{format_otp_login_message(code, settings)}\n\nشماره درخواست‌کننده: {phone}"
    
    message = f"{chat_id}|{text}".encode("utf-8")
    secret = settings.telegram_bridge_secret.encode("utf-8")
    signature = hmac.new(secret, message, hashlib.sha256).hexdigest()
    
    return {
        "chat_id": chat_id,
        "text": text,
        "signature": signature
    }


def format_otp_login_message(code: str, settings: Settings) -> str:
    provider = settings.otp_provider.lower()
    template = settings.smsir_message_template if provider in ("smsir", "sms.ir") else settings.kavenegar_message_template
    return _unescape_template(template).format(code=code)


def verify_otp(phone: str, code: str, referral_code: str | None = None) -> tuple[str, str, int]:
    settings = get_runtime_settings()
    normalized_phone = normalize_digits(phone)
    normalized_code = normalize_digits(code)
    with db() as conn:
        otp = conn.execute("SELECT * FROM auth_otps WHERE phone = ?", (normalized_phone,)).fetchone()
        if not otp or otp["code"] != normalized_code:
            if otp:
                conn.execute("UPDATE auth_otps SET attempts = attempts + 1 WHERE phone = ?", (normalized_phone,))
            raise HTTPException(status_code=401, detail="Invalid OTP code")
        if otp["consumed_at"]:
            raise HTTPException(status_code=401, detail="OTP code has already been used")
        if int(otp["attempts"] or 0) >= settings.otp_max_attempts:
            raise HTTPException(status_code=429, detail="Too many OTP attempts")
        expires_at = _parse_iso(otp["expires_at"])
        created_at = _parse_iso(otp["created_at"])
        if expires_at is None and created_at is not None:
            expires_at = created_at + timedelta(seconds=settings.otp_ttl_seconds)
        if expires_at is not None and _utc_now() > expires_at:
            raise HTTPException(status_code=401, detail="OTP code has expired")

        user = conn.execute("SELECT * FROM users WHERE phone = ?", (normalized_phone,)).fetchone()
        if user is None:
            user_id = new_id("user")
            bonus = max(0, settings.signup_bonus_credits)
            own_referral_code = generate_referral_code()
            referrer = _find_referrer(conn, referral_code)
            conn.execute(
                """
                INSERT INTO users (id, phone, created_at, credit_balance, source_channel, referral_code, referred_by_user_id)
                VALUES (?, ?, ?, ?, 'web', ?, ?)
                """,
                (user_id, normalized_phone, now_iso(), bonus, own_referral_code, referrer["id"] if referrer else None),
            )
            if referrer:
                conn.execute("UPDATE users SET credit_balance = credit_balance + 5, referral_awarded_at = COALESCE(referral_awarded_at, ?) WHERE id = ?", (now_iso(), referrer["id"]))
            credit_balance = bonus
        else:
            user_id = user["id"]
            credit_balance = int(user["credit_balance"])
            if not user["referral_code"]:
                conn.execute("UPDATE users SET referral_code = ? WHERE id = ?", (generate_referral_code(), user_id))

        token = new_id("sess")
        session_ttl = settings.session_ttl_days
        expires_at = (_utc_now() + timedelta(days=session_ttl)).isoformat()
        conn.execute(
            "INSERT INTO auth_sessions (token, user_id, created_at, expires_at) VALUES (?, ?, ?, ?)",
            (token, user_id, now_iso(), expires_at),
        )
        conn.execute("UPDATE auth_otps SET consumed_at = ? WHERE phone = ?", (now_iso(), normalized_phone))
        return token, user_id, credit_balance


def get_runtime_settings() -> Settings:
    from app.config import get_settings

    return get_settings()


def generate_referral_code() -> str:
    return secrets.token_urlsafe(6).replace("-", "").replace("_", "")[:8].upper()


def _find_referrer(conn, referral_code: str | None):
    if not referral_code:
        return None
    normalized = referral_code.strip().upper()
    if not normalized:
        return None
    return conn.execute("SELECT id FROM users WHERE referral_code = ?", (normalized,)).fetchone()


def get_current_user_id(authorization: str | None = Header(default=None)) -> str:
    if not authorization or not authorization.startswith("Bearer "):
        raise HTTPException(status_code=401, detail="Missing bearer token")
    token = authorization.removeprefix("Bearer ").strip()
    with db() as conn:
        row = conn.execute(
            "SELECT user_id, expires_at FROM auth_sessions WHERE token = ?", (token,)
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=401, detail="Invalid session")
    expires_at = _parse_iso(row["expires_at"])
    if expires_at is not None and _utc_now() > expires_at:
        raise HTTPException(status_code=401, detail="Session expired")
    return str(row["user_id"])
