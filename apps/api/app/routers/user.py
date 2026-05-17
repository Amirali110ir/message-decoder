from fastapi import APIRouter, Depends

from app.database import db
from app.schemas import CreditsOut
from app.services.auth import get_current_user_id

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/credits", response_model=CreditsOut)
def credits(user_id: str = Depends(get_current_user_id)) -> CreditsOut:
    with db() as conn:
        row = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (user_id,)).fetchone()
    return CreditsOut(credit_balance=int(row["credit_balance"]) if row else 0)

