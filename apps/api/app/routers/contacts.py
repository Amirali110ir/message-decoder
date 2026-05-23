from uuid import uuid4
import datetime
from fastapi import APIRouter, Depends, HTTPException

from app.database import db
from app.schemas import ContactIn, ContactOut, OkOut, RelationshipThermometerOut
from app.services.auth import get_current_user_id

router = APIRouter(prefix="/contacts", tags=["contacts"])


@router.get("", response_model=list[ContactOut])
def get_contacts(user_id: str = Depends(get_current_user_id)) -> list[ContactOut]:
    with db() as conn:
        rows = conn.execute(
            "SELECT * FROM contacts WHERE user_id = ? ORDER BY interaction_count DESC, name ASC",
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


@router.post("", response_model=ContactOut, status_code=201)
def create_contact(
    payload: ContactIn, user_id: str = Depends(get_current_user_id)
) -> ContactOut:
    contact_id = str(uuid4())
    created_at = datetime.datetime.now(datetime.timezone.utc).isoformat()
    with db() as conn:
        conn.execute(
            """
            INSERT INTO contacts (id, user_id, name, relationship_type, default_goal, profile_summary, interaction_count, created_at)
            VALUES (?, ?, ?, ?, ?, ?, 0, ?)
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


@router.get("/{contact_id}/thermometer", response_model=RelationshipThermometerOut)
def relationship_thermometer(
    contact_id: str,
    user_id: str = Depends(get_current_user_id),
) -> RelationshipThermometerOut:
    with db() as conn:
        contact = conn.execute(
            "SELECT interaction_count FROM contacts WHERE id = ? AND user_id = ?",
            (contact_id, user_id),
        ).fetchone()
        if not contact:
            raise HTTPException(status_code=404, detail="مخاطب یافت نشد.")
        rows = conn.execute(
            """
            SELECT d.dominant_lens, d.confidence_level, m.safety_label, d.created_at
            FROM decodes d
            JOIN messages m ON m.id = d.message_id
            WHERE m.contact_id = ? AND m.user_id = ?
            ORDER BY d.created_at DESC
            LIMIT 20
            """,
            (contact_id, user_id),
        ).fetchall()

    defensive_points = 0
    warmth_points = 50
    for row in rows:
        if row["dominant_lens"] == "serotonin":
            defensive_points += 12
            warmth_points -= 6
        elif row["dominant_lens"] == "dopamine":
            defensive_points += 6
            warmth_points -= 2
        elif row["dominant_lens"] == "oxytocin":
            defensive_points -= 5
            warmth_points += 4
        if row["safety_label"] == "watch":
            defensive_points += 12
            warmth_points -= 8
        elif row["safety_label"] == "high_risk":
            defensive_points += 25
            warmth_points -= 18

    sample_size = max(1, len(rows))
    defensive_trend = max(-100, min(100, round(defensive_points / sample_size * 3)))
    warmth_score = max(0, min(100, round(warmth_points)))
    if not rows:
        label = "داده کم"
        summary = "برای این مخاطب هنوز تحلیل کافی ثبت نشده است."
    elif defensive_trend >= 35:
        label = "رو به تدافعی‌تر شدن"
        summary = "در تحلیل‌های اخیر نشانه‌های دفاعی یا حساسیت به شأن بیشتر دیده می‌شود."
    elif defensive_trend <= -15:
        label = "رو به گرم‌تر شدن"
        summary = "در تحلیل‌های اخیر نیاز به اطمینان و ترمیم بیشتر از تنش دفاعی دیده می‌شود."
    else:
        label = "نسبتاً پایدار"
        summary = "روند اخیر این رابطه تغییر تند یا پرریسکی نشان نمی‌دهد."

    return RelationshipThermometerOut(
        contact_id=contact_id,
        interaction_count=int(contact["interaction_count"]),
        defensive_trend=defensive_trend,
        warmth_score=warmth_score,
        label=label,
        summary=summary,
    )
