from typing import Optional

from fastapi import APIRouter, Header

from app.database import db
from app.schemas import CopyEventIn, FeedbackIn, OkOut, SelectedReplyFeedbackIn
from app.services.analytics import track
from app.services.learning import record_quality_signal
from app.utils import new_id, now_iso

router = APIRouter(tags=["feedback"])


@router.post("/feedback", response_model=OkOut)
def feedback(payload: FeedbackIn) -> OkOut:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO feedback (
                id, decode_id, user_rating, favorite_reply_label, copied_response,
                sent_response, outcome, regret_score, user_comment, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("fb"),
                payload.decode_id,
                payload.user_rating,
                payload.favorite_reply_label,
                None if payload.copied_response is None else int(payload.copied_response),
                payload.sent_response,
                payload.outcome,
                payload.regret_score,
                payload.user_comment,
                now_iso(),
            ),
        )
    track("feedback_submitted", payload={"decode_id": payload.decode_id, "outcome": payload.outcome})
    if payload.user_rating:
        record_quality_signal(payload.decode_id, "user_rating", payload.user_rating, "feedback", 1)
    if payload.outcome:
        record_quality_signal(payload.decode_id, "outcome", payload.outcome, "feedback", 1.5)
    if payload.regret_score is not None:
        record_quality_signal(payload.decode_id, "regret_score", str(payload.regret_score), "feedback", 2)
    if payload.favorite_reply_label:
        record_quality_signal(payload.decode_id, "favorite_reply_label", payload.favorite_reply_label, "feedback", 1)
    if payload.outcome:
        track("outcome_submitted", payload={"decode_id": payload.decode_id, "outcome": payload.outcome})
    return OkOut(ok=True)


@router.post("/feedback/selected-reply", response_model=OkOut)
def selected_reply_feedback(payload: SelectedReplyFeedbackIn, authorization: Optional[str] = Header(None)) -> OkOut:
    user_id = _optional_user_id(authorization)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO feedback (
                id, decode_id, favorite_reply_label, selected_reply_label,
                copied_response, outcome, created_at
            ) VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (
                new_id("fb"),
                payload.decode_id,
                payload.selected_reply_label,
                payload.selected_reply_label,
                None if payload.copied_response is None else int(payload.copied_response),
                payload.outcome,
                now_iso(),
            ),
        )
        contact_id = payload.contact_id
        if not contact_id and user_id:
            row = conn.execute(
                """
                SELECT m.contact_id
                FROM decodes d
                JOIN messages m ON m.id = d.message_id
                WHERE d.id = ? AND m.user_id = ?
                """,
                (payload.decode_id, user_id),
            ).fetchone()
            contact_id = row["contact_id"] if row else None
        if contact_id and user_id:
            existing = conn.execute(
                "SELECT profile_summary FROM contacts WHERE id = ? AND user_id = ?",
                (contact_id, user_id),
            ).fetchone()
            if existing:
                conn.execute(
                    "UPDATE contacts SET profile_summary = ? WHERE id = ? AND user_id = ?",
                    (
                        _updated_profile_summary(
                            existing["profile_summary"],
                            payload.selected_reply_label,
                            payload.outcome,
                        ),
                        contact_id,
                        user_id,
                    ),
                )
    track(
        "selected_reply_submitted",
        payload={
            "decode_id": payload.decode_id,
            "selected_reply_label": payload.selected_reply_label,
            "outcome": payload.outcome,
        },
    )
    record_quality_signal(payload.decode_id, "selected_reply_label", payload.selected_reply_label, "selected_reply", 2)
    if payload.outcome:
        record_quality_signal(payload.decode_id, "selected_reply_outcome", payload.outcome, "selected_reply", 2)
    return OkOut(ok=True)


@router.post("/copy-event", response_model=OkOut)
def copy_event(payload: CopyEventIn) -> OkOut:
    with db() as conn:
        conn.execute(
            "INSERT INTO copy_events (id, decode_id, reply_label, reply_text_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (new_id("copy"), payload.decode_id, payload.reply_label, payload.reply_text_id, now_iso()),
        )
    track("reply_copied", payload={"decode_id": payload.decode_id, "reply_label": payload.reply_label})
    record_quality_signal(payload.decode_id, "reply_copied", payload.reply_label, "copy_event", 1)
    return OkOut(ok=True)


def _optional_user_id(authorization: str | None) -> str | None:
    if not authorization or not authorization.startswith("Bearer "):
        return None
    token = authorization.removeprefix("Bearer ").strip()
    with db() as conn:
        row = conn.execute("SELECT user_id FROM auth_sessions WHERE token = ?", (token,)).fetchone()
    return str(row["user_id"]) if row else None


def _updated_profile_summary(existing: str | None, selected_reply_label: str, outcome: str | None) -> str:
    signal = f"کاربر اخیراً پاسخ «{selected_reply_label}» را برای این مخاطب انتخاب کرد"
    if outcome:
        signal = f"{signal} و نتیجه را «{outcome}» گزارش کرد"
    signal = f"{signal}."
    parts = [part.strip() for part in (existing, signal) if part and part.strip()]
    summary = " ".join(parts)
    return summary[:2000]
