from fastapi import APIRouter

from app.config import get_settings
from app.schemas import RequestOtpIn, RequestOtpOut, VerifyOtpIn, VerifyOtpOut
from app.services.auth import create_or_update_otp, verify_otp

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/request-otp", response_model=RequestOtpOut)
def request_otp(payload: RequestOtpIn) -> RequestOtpOut:
    settings = get_settings()
    create_or_update_otp(payload.phone, settings.dev_otp_code)
    return RequestOtpOut(ok=True, dev_otp_code=settings.dev_otp_code if settings.otp_provider == "mock" else None)


@router.post("/verify-otp", response_model=VerifyOtpOut)
def verify(payload: VerifyOtpIn) -> VerifyOtpOut:
    token, user_id, credit_balance = verify_otp(payload.phone, payload.code)
    return VerifyOtpOut(token=token, user_id=user_id, credit_balance=credit_balance)

