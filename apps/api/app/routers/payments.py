from fastapi import APIRouter, Depends

from app.schemas import PaymentCreateIn, PaymentCreateOut, PaymentVerifyIn, PaymentVerifyOut
from app.services.analytics import track
from app.services.auth import get_current_user_id
from app.services.payments import create_payment, verify_payment

router = APIRouter(prefix="/payment", tags=["payment"])


@router.post("/create", response_model=PaymentCreateOut)
def create(payload: PaymentCreateIn, user_id: str = Depends(get_current_user_id)) -> PaymentCreateOut:
    payment = create_payment(user_id, payload.package_id)
    track("paywall_viewed", user_id=user_id, payload={"package_id": payload.package_id})
    return PaymentCreateOut(**payment)


@router.post("/verify", response_model=PaymentVerifyOut)
def verify(payload: PaymentVerifyIn, user_id: str = Depends(get_current_user_id)) -> PaymentVerifyOut:
    status, balance = verify_payment(user_id, payload.payment_id, payload.status)
    if status == "verified":
        track("credit_purchased", user_id=user_id, payload={"payment_id": payload.payment_id})
    return PaymentVerifyOut(payment_id=payload.payment_id, status=status, credit_balance=balance)
