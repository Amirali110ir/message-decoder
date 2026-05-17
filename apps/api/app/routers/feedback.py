from fastapi import APIRouter

from app.database import db
from app.schemas import CopyEventIn, FeedbackIn, OkOut
from app.services.analytics import track
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
    if payload.outcome:
        track("outcome_submitted", payload={"decode_id": payload.decode_id, "outcome": payload.outcome})
    return OkOut(ok=True)


@router.post("/copy-event", response_model=OkOut)
def copy_event(payload: CopyEventIn) -> OkOut:
    with db() as conn:
        conn.execute(
            "INSERT INTO copy_events (id, decode_id, reply_label, reply_text_id, created_at) VALUES (?, ?, ?, ?, ?)",
            (new_id("copy"), payload.decode_id, payload.reply_label, payload.reply_text_id, now_iso()),
        )
    track("reply_copied", payload={"decode_id": payload.decode_id, "reply_label": payload.reply_label})
    return OkOut(ok=True)
