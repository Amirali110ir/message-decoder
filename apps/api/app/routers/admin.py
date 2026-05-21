from fastapi import APIRouter, Header, HTTPException

from app.config import get_settings
from app.database import db
from app.schemas import FreeDecodeIn
from app.services.learning import build_daily_learning_report
from app.services.rule_engine import classification_payload, classify, paid_reply_playbook
from app.services.rule_eval import candidate_eval_cases, evaluate_rule_engine

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
