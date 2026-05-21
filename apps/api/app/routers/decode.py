from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from app.database import db
from app.schemas import FreeDecodeIn, FreeDecodeResponse, PaidDecodeIn, PaidDecodeResponse
from app.services.analytics import track
from app.services.ai import (
    OUTPUT_SCHEMA_VERSION,
    PROMPT_VERSION,
    RULE_ENGINE_VERSION,
    classify,
    current_model_version,
    free_decode,
    paid_decode,
    safety_output,
)
from app.services.auth import get_current_user_id
from app.utils import anonymize_text, dumps, loads, new_id, now_iso

router = APIRouter(tags=["decode"])


@router.post("/decode/free", response_model=FreeDecodeResponse)
async def create_free_decode(payload: FreeDecodeIn) -> FreeDecodeResponse:
    classification = classify(payload)
    message_id = new_id("msg")
    decode_id = new_id("dec")
    raw_text = payload.message_text if payload.privacy_consent == "history" else None
    anonymized = anonymize_text(payload.message_text) if payload.privacy_consent in ("history", "anonymized") else None
    output = safety_output() if classification.safety_label == "high_risk" else await free_decode(payload, classification)
    with db() as conn:
        conn.execute(
            """
            INSERT INTO messages (
                id, user_id, raw_text, anonymized_text, relationship_type, user_goal,
                optional_context, privacy_consent, safety_label, created_at
            ) VALUES (?, NULL, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                message_id,
                raw_text,
                anonymized,
                payload.relationship_type,
                payload.user_goal,
                payload.optional_context,
                payload.privacy_consent,
                classification.safety_label,
                now_iso(),
            ),
        )
        conn.execute(
            """
            INSERT INTO decodes (
                id, message_id, dominant_lens, secondary_lenses, confidence_level,
                free_output, model_version, free_model_version, prompt_version,
                rule_engine_version, output_schema_version, created_at
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                decode_id,
                message_id,
                classification.dominant_lens,
                dumps(classification.secondary_lenses),
                classification.confidence,
                dumps(output.model_dump()),
                current_model_version("free"),
                current_model_version("free"),
                PROMPT_VERSION,
                RULE_ENGINE_VERSION,
                OUTPUT_SCHEMA_VERSION,
                now_iso(),
            ),
        )
    if classification.safety_label == "high_risk":
        track("message_submitted", payload={"decode_id": decode_id, "relationship_type": payload.relationship_type})
        track("free_decode_generated", payload={"decode_id": decode_id, "safety_label": classification.safety_label})
        return FreeDecodeResponse(
            decode_id=decode_id,
            safety_label=classification.safety_label,
            safety_output=output,
            prompt_version=PROMPT_VERSION,
            model_version=current_model_version(),
        )
    track("message_submitted", payload={"decode_id": decode_id, "relationship_type": payload.relationship_type})
    track("free_decode_generated", payload={"decode_id": decode_id, "safety_label": classification.safety_label})
    return FreeDecodeResponse(
        decode_id=decode_id,
        safety_label=classification.safety_label,
        free_output=output,
        prompt_version=PROMPT_VERSION,
        model_version=current_model_version(),
    )


@router.post("/decode/paid", response_model=PaidDecodeResponse)
async def create_paid_decode(payload: PaidDecodeIn, user_id: str = Depends(get_current_user_id)) -> PaidDecodeResponse:
    generated_paid = False
    with db() as conn:
        user = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (user_id,)).fetchone()
        if user is None:
            raise HTTPException(status_code=401, detail="User not found")
        if int(user["credit_balance"]) < 1:
            raise HTTPException(status_code=402, detail="Insufficient credits")

        decode = conn.execute(
            """
            SELECT d.*, m.relationship_type, m.user_goal
            FROM decodes d
            JOIN messages m ON m.id = d.message_id
            WHERE d.id = ?
            """,
            (payload.decode_id,),
        ).fetchone()
        if decode is None:
            raise HTTPException(status_code=404, detail="Decode not found")
        if decode["paid_output"]:
            paid = loads(decode["paid_output"])
        else:
            if loads(decode["free_output"], {}).get("warning_title"):
                raise HTTPException(status_code=400, detail="Safety decodes do not support paid replies")
            free_output = loads(decode["free_output"])
            paid_model = await paid_decode(
                free_decode_output_from_dict(free_output),
                decode["relationship_type"],
                decode["user_goal"],
            )
            paid = paid_model.model_dump()
            conn.execute(
                "UPDATE decodes SET paid_output = ?, paid_model_version = ?, paid_at = ? WHERE id = ?",
                (dumps(paid), current_model_version("paid"), now_iso(), payload.decode_id),
            )
            conn.execute("UPDATE users SET credit_balance = credit_balance - 1 WHERE id = ?", (user_id,))
            generated_paid = True

        balance = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (user_id,)).fetchone()["credit_balance"]
    if generated_paid:
        track("paid_decode_generated", user_id=user_id, payload={"decode_id": payload.decode_id})
    return PaidDecodeResponse(decode_id=payload.decode_id, paid_output=paid, credit_balance=int(balance))



def free_decode_output_from_dict(data: dict):
    from app.schemas import FreeDecodeOutput

    return FreeDecodeOutput.model_validate(data)


@router.get("/decode/{decode_id}")
def get_decode(decode_id: str, user_id: str = Depends(get_current_user_id)):
    with db() as conn:
        row = conn.execute(
            """
            SELECT d.id, d.dominant_lens, d.secondary_lenses, d.confidence_level, d.free_output, d.paid_output,
                   d.model_version, d.prompt_version, m.relationship_type, m.user_goal, m.safety_label
            FROM decodes d
            JOIN messages m ON m.id = d.message_id
            WHERE d.id = ?
            """,
            (decode_id,),
        ).fetchone()
    if row is None:
        raise HTTPException(status_code=404, detail="Decode not found")
    return dict(row)
