from fastapi import APIRouter, Header, HTTPException, Query

from app.config import get_settings
from app.database import db
from app.schemas import AdminDecodeItem, AdminDecodeListOut, FreeDecodeIn
from app.services.learning import build_daily_learning_report
from app.services.rule_engine import classification_payload, classify, paid_reply_playbook
from app.services.rule_eval import candidate_eval_cases, evaluate_rule_engine
from app.utils import loads

router = APIRouter(prefix="/admin", tags=["admin"])


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    if x_admin_token != get_settings().admin_token:
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.get("/metrics")
def metrics(_: None = Header(default=None), x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    with db() as conn:
        users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        decodes = conn.execute("SELECT COUNT(*) AS c FROM decodes").fetchone()["c"]
        paid = conn.execute("SELECT COUNT(*) AS c FROM decodes WHERE paid_output IS NOT NULL").fetchone()["c"]
        copies = conn.execute("SELECT COUNT(*) AS c FROM copy_events").fetchone()["c"]
        revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) AS s FROM payments WHERE status = 'verified'").fetchone()["s"]
        by_lens = [dict(row) for row in conn.execute("SELECT dominant_lens, COUNT(*) AS count FROM decodes GROUP BY dominant_lens")]
        safety = [dict(row) for row in conn.execute("SELECT safety_label, COUNT(*) AS count FROM messages GROUP BY safety_label")]
    conversion = paid / decodes if decodes else 0
    copy_rate = copies / paid if paid else 0
    return {
        "users": users,
        "free_decodes": decodes,
        "paid_decodes": paid,
        "revenue": revenue,
        "conversion": conversion,
        "copy_rate": copy_rate,
        "by_lens": by_lens,
        "safety": safety,
    }


@router.get("/decodes", response_model=AdminDecodeListOut)
def decode_listing(
    relationship_type: str | None = None,
    dominant_lens: str | None = None,
    safety_label: str | None = None,
    prompt_version: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    x_admin_token: str | None = Header(default=None),
) -> AdminDecodeListOut:
    require_admin(x_admin_token)
    filters: list[str] = []
    params: list[str | int] = []
    if relationship_type:
        filters.append("m.relationship_type = ?")
        params.append(relationship_type)
    if dominant_lens:
        filters.append("d.dominant_lens = ?")
        params.append(dominant_lens)
    if safety_label:
        filters.append("m.safety_label = ?")
        params.append(safety_label)
    if prompt_version:
        filters.append("d.prompt_version = ?")
        params.append(prompt_version)

    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    with db() as conn:
        total = conn.execute(
            f"""
            SELECT COUNT(*) AS c
            FROM decodes d
            JOIN messages m ON m.id = d.message_id
            {where}
            """,
            params,
        ).fetchone()["c"]
        rows = conn.execute(
            f"""
            SELECT
                d.id,
                d.created_at,
                d.paid_at,
                d.dominant_lens,
                d.secondary_lenses,
                d.confidence_level,
                d.model_version,
                d.free_model_version,
                d.paid_model_version,
                d.prompt_version,
                d.rule_engine_version,
                d.output_schema_version,
                d.paid_output IS NOT NULL AS has_paid_output,
                m.relationship_type,
                m.user_goal,
                m.privacy_consent,
                m.safety_label,
                m.anonymized_text,
                (SELECT COUNT(*) FROM feedback f WHERE f.decode_id = d.id) AS feedback_count,
                (SELECT COUNT(*) FROM copy_events c WHERE c.decode_id = d.id) AS copy_count
            FROM decodes d
            JOIN messages m ON m.id = d.message_id
            {where}
            ORDER BY d.created_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()

    items = [
        AdminDecodeItem(
            id=row["id"],
            created_at=row["created_at"],
            paid_at=row["paid_at"],
            relationship_type=row["relationship_type"],
            user_goal=row["user_goal"],
            privacy_consent=row["privacy_consent"],
            safety_label=row["safety_label"],
            dominant_lens=row["dominant_lens"],
            secondary_lenses=loads(row["secondary_lenses"], []),
            confidence_level=row["confidence_level"],
            prompt_version=row["prompt_version"],
            model_version=row["model_version"],
            free_model_version=row["free_model_version"],
            paid_model_version=row["paid_model_version"],
            rule_engine_version=row["rule_engine_version"],
            output_schema_version=row["output_schema_version"],
            has_paid_output=bool(row["has_paid_output"]),
            anonymized_preview=_preview(row["anonymized_text"]),
            feedback_count=int(row["feedback_count"]),
            copy_count=int(row["copy_count"]),
        )
        for row in rows
    ]
    return AdminDecodeListOut(items=items, total=total, limit=limit, offset=offset)


@router.get("/learning/daily")
def daily_learning_report(
    report_date: str | None = None,
    persist: bool = False,
    x_admin_token: str | None = Header(default=None),
):
    require_admin(x_admin_token)
    return build_daily_learning_report(report_date=report_date, persist=persist)


@router.post("/rule-engine/explain")
def explain_rule_engine(payload: FreeDecodeIn, x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    classification = classify(payload)
    return {
        "analysis": classification_payload(classification),
        "paid_reply_playbook": paid_reply_playbook(
            payload.relationship_type,
            payload.user_goal,
            classification.dominant_lens,
        ),
    }


@router.get("/rule-engine/eval")
def rule_engine_eval(x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    return evaluate_rule_engine()


@router.get("/rule-engine/candidate-cases")
def rule_engine_candidate_cases(limit: int = 50, x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    return candidate_eval_cases(limit=limit)


def _preview(value: str | None, max_length: int = 180) -> str | None:
    if not value:
        return None
    clean = " ".join(value.split())
    if len(clean) <= max_length:
        return clean
    return f"{clean[:max_length - 1]}…"
