from uuid import uuid4
import datetime
from fastapi import APIRouter, Depends, HTTPException

from app.database import db
from app.schemas import ContactIn, ContactOut, OkOut
from app.services.auth import get_current_user_id

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactOut])
def get_contacts(user_id: str = Depends(get_current_user_id)) -> list[ContactOut]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM contacts WHERE user_id = ? ORDER BY name ASC",
            (user_id,),
        ).fetchall()
    return [
        ContactOut(
            id=row["id"],
            name=row["name"],
            relationship_type=row["relationship_type"],
            default_goal=row["default_goal"],
            profile_summary=row["profile_summary"],
            interaction_count=row["interaction_count"],
            created_at=row["created_at"],
        )
        for row in rows
    ]


@router.post("", response_model=ContactOut)
def create_contact(
    payload: ContactIn, user_id: str = Depends(get_current_user_id)
) -> ContactOut:
    contact_id = str(uuid4())
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO contacts (id, user_id, name, relationship_type, default_goal, profile_summary, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                contact_id,
                user_id,
                payload.name,
                payload.relationship_type,
                payload.default_goal,
                payload.profile_summary,
                created_at,
            ),
        )
    return ContactOut(
        id=contact_id,
        name=payload.name,
        relationship_type=payload.relationship_type,
        default_goal=payload.default_goal,
        profile_summary=payload.profile_summary,
        interaction_count=0,
        created_at=created_at,
    )


@router.put("/{contact_id}", response_model=ContactOut)
def update_contact(
    contact_id: str,
    payload: ContactIn,
    user_id: str = Depends(get_current_user_id),
) -> ContactOut:
    with db() as conn:
        row = conn.execute(
            "SELECT id, interaction_count, created_at FROM contacts WHERE id = ? AND user_id = ?",
            (contact_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="مخاطب یافت نشد.")

        conn.execute(
            """
            UPDATE contacts
            SET name = ?, relationship_type = ?, default_goal = ?, profile_summary = ?
            WHERE id = ? AND user_id = ?
            """,
            (
                payload.name,
                payload.relationship_type,
                payload.default_goal,
                payload.profile_summary,
                contact_id,
                user_id,
            ),
        )

    return ContactOut(
        id=contact_id,
        name=payload.name,
        relationship_type=payload.relationship_type,
        default_goal=payload.default_goal,
        profile_summary=payload.profile_summary,
        interaction_count=row["interaction_count"],
        created_at=row["created_at"],
    )


@router.delete("/{contact_id}", response_model=OkOut)
def delete_contact(
    contact_id: str, user_id: str = Depends(get_current_user_id)
) -> OkOut:
    with db() as conn:
        row = conn.execute(
            "SELECT id FROM contacts WHERE id = ? AND user_id = ?",
            (contact_id, user_id),
        ).fetchone()
        if not row:
            raise HTTPException(status_code=404, detail="مخاطب یافت نشد.")

        conn.execute(
            "DELETE FROM contacts WHERE id = ? AND user_id = ?",
            (contact_id, user_id),
        )
    return OkOut(ok=True)
