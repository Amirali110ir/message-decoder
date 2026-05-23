from fastapi import APIRouter, Depends

from app.database import db
from app.schemas import CreditsOut, DeletedStoredDataOut
from app.services.auth import get_current_user_id
from app.services.privacy import delete_messages_with_decodes

router = APIRouter(prefix="/user", tags=["user"])


@router.get("/credits", response_model=CreditsOut)
def credits(user_id: str = Depends(get_current_user_id)) -> CreditsOut:
    with db() as conn:
        row = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (user_id,)).fetchone()
    return CreditsOut(credit_balance=int(row["credit_balance"]) if row else 0)


@router.delete("/stored-data", response_model=DeletedStoredDataOut)
def delete_stored_data(user_id: str = Depends(get_current_user_id)) -> DeletedStoredDataOut:
    with db() as conn:
        message_ids = [
            str(row["id"])
            for row in conn.execute("SELECT id FROM messages WHERE user_id = ?", (user_id,)).fetchall()
        ]
        deleted_decodes, deleted_messages = delete_messages_with_decodes(conn, message_ids)
        deleted_contacts = conn.execute("SELECT COUNT(*) AS c FROM contacts WHERE user_id = ?", (user_id,)).fetchone()["c"]
        conn.execute("DELETE FROM contacts WHERE user_id = ?", (user_id,))
    return DeletedStoredDataOut(
        ok=True,
        deleted_decodes=deleted_decodes,
        deleted_messages=deleted_messages,
        deleted_contacts=int(deleted_contacts),
    )
