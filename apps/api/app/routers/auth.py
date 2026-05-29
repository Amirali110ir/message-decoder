from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.database import db
from app.schemas import RequestOtpIn, RequestOtpOut, TelegramLinkIn, TelegramOtpPayloadIn, TelegramOtpPayloadOut, VerifyOtpIn, VerifyOtpOut
from app.services.auth import format_otp_login_message, normalize_digits, request_otp_code, verify_otp

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/request-otp", response_model=RequestOtpOut)
def request_otp(payload: RequestOtpIn) -> RequestOtpOut:
    settings = get_settings()
    dev_otp_code, telegram_payload = request_otp_code(payload.phone, settings)
    return RequestOtpOut(ok=True, dev_otp_code=dev_otp_code, telegram_payload=telegram_payload)


@router.post("/verify-otp", response_model=VerifyOtpOut)
def verify(payload: VerifyOtpIn) -> VerifyOtpOut:
    token, user_id, credit_balance = verify_otp(payload.phone, payload.code, payload.referral_code)
    return VerifyOtpOut(token=token, user_id=user_id, credit_balance=credit_balance)


@router.post("/telegram-otp-payload", response_model=TelegramOtpPayloadOut)
def telegram_otp_payload(
    payload: TelegramOtpPayloadIn,
    x_telegram_bridge_secret: str | None = Header(default=None),
) -> TelegramOtpPayloadOut:
    settings = get_settings()
    if not settings.telegram_bridge_secret or x_telegram_bridge_secret != settings.telegram_bridge_secret:
        raise HTTPException(status_code=401, detail="Invalid telegram bridge secret")

    phone = normalize_digits(payload.phone)
    with db() as conn:
        row = conn.execute(
            """
            SELECT u.telegram_id, o.code
            FROM users u
            JOIN auth_otps o ON o.phone = u.phone
            WHERE u.phone = ? AND u.telegram_id IS NOT NULL AND o.consumed_at IS NULL
            """,
            (phone,),
        ).fetchone()
    if not row:
        return TelegramOtpPayloadOut(ok=False)
    return TelegramOtpPayloadOut(
        ok=True,
        chat_id=str(row["telegram_id"]),
        text=format_otp_login_message(str(row["code"]), settings),
    )


@router.post("/telegram-link")
def telegram_link(
    payload: TelegramLinkIn,
    x_telegram_bridge_secret: str | None = Header(default=None),
) -> dict[str, bool]:
    settings = get_settings()
    if not settings.telegram_bridge_secret or x_telegram_bridge_secret != settings.telegram_bridge_secret:
        raise HTTPException(status_code=401, detail="Invalid telegram bridge secret")
    phone = normalize_digits(payload.phone)
    with db() as conn:
        user = conn.execute("SELECT id FROM users WHERE phone = ?", (phone,)).fetchone()
        if user:
            conn.execute("UPDATE users SET telegram_id = ? WHERE id = ?", (payload.telegram_id, user["id"]))
        else:
            conn.execute(
                """
                INSERT INTO users (id, phone, telegram_id, created_at, credit_balance, source_channel, referral_code)
                VALUES (?, ?, ?, datetime('now'), ?, 'telegram', ?)
                """,
                (f"user_{payload.telegram_id}", phone, payload.telegram_id, max(0, settings.signup_bonus_credits), ""),
            )
    return {"ok": True}
