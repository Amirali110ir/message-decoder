import hmac
import os
import sqlite3
import tempfile
from datetime import date, datetime, timedelta, timezone

from fastapi import APIRouter, Depends, Header, HTTPException, Query
from fastapi.responses import StreamingResponse

from app.config import get_settings
from app.database import db
from app.schemas import (
    AdminActivityItem,
    AdminActivityListOut,
    AdminLoginIn,
    AdminLoginOut,
    AdminBulkGrantCreditsIn,
    AdminBulkGrantCreditsOut,
    AdminDecodeItem,
    AdminDecodeListOut,
    AdminGrantCreditsIn,
    AdminGrantCreditsOut,
    AdminUserItem,
    AdminUserListOut,
    FreeDecodeIn,
)
from app.services.analytics import retention_metrics, usage_frequency
from app.services.learning import build_daily_learning_report
from app.services.rule_engine import classification_payload, classify, paid_reply_playbook
from app.services.rule_eval import candidate_eval_cases, evaluate_rule_engine
from app.services.auth import normalize_digits
from app.utils import loads

router = APIRouter(prefix="/admin", tags=["admin"])


def normalize_phone(value: str) -> str:
    return normalize_digits(value)


def phone_variants(value: str | None) -> list[str]:
    if not value:
        return []
    normalized = normalize_phone(value)
    variants = {normalized}
    if normalized.startswith("0"):
        variants.add("98" + normalized[1:])
        variants.add("+98" + normalized[1:])
    return list(variants)


def require_admin(x_admin_token: str | None = Header(default=None)) -> None:
    settings = get_settings()
    if not x_admin_token or not hmac.compare_digest(x_admin_token, settings.admin_token):
        raise HTTPException(status_code=401, detail="Invalid admin token")


@router.post("/login", response_model=AdminLoginOut)
def admin_login(payload: AdminLoginIn) -> AdminLoginOut:
    settings = get_settings()
    if not settings.admin_phone or not settings.admin_password or not settings.admin_token:
        raise HTTPException(status_code=503, detail="Admin login is not configured")

    phone = normalize_phone(payload.phone)
    _raise_if_admin_login_locked(phone)
    phone_ok = hmac.compare_digest(phone, normalize_phone(settings.admin_phone))
    password_ok = hmac.compare_digest(payload.password, settings.admin_password)
    if not phone_ok or not password_ok:
        _record_admin_login_failure(phone)
        raise HTTPException(status_code=401, detail="شماره یا رمز ادمین درست نیست")

    _clear_admin_login_failures(phone)
    return AdminLoginOut(token=settings.admin_token)


def _raise_if_admin_login_locked(phone: str) -> None:
    with db() as conn:
        row = conn.execute("SELECT locked_until FROM admin_login_attempts WHERE phone = ?", (phone,)).fetchone()
    if not row or not row["locked_until"]:
        return
    try:
        locked_until = datetime.fromisoformat(row["locked_until"])
    except ValueError:
        return
    if locked_until > datetime.now(timezone.utc):
        raise HTTPException(status_code=429, detail="ورود ادمین موقتاً قفل شده است. چند دقیقه دیگر دوباره تلاش کنید.")


def _record_admin_login_failure(phone: str) -> None:
    now_dt = datetime.now(timezone.utc)
    with db() as conn:
        row = conn.execute("SELECT failed_count FROM admin_login_attempts WHERE phone = ?", (phone,)).fetchone()
        failed_count = int(row["failed_count"]) + 1 if row else 1
        locked_until = (now_dt + timedelta(minutes=10)).isoformat() if failed_count >= 5 else None
        conn.execute(
            """
            INSERT INTO admin_login_attempts (phone, failed_count, locked_until, updated_at)
            VALUES (?, ?, ?, ?)
            ON CONFLICT(phone) DO UPDATE SET
                failed_count = excluded.failed_count,
                locked_until = excluded.locked_until,
                updated_at = excluded.updated_at
            """,
            (phone, failed_count, locked_until, now_dt.isoformat()),
        )


def _clear_admin_login_failures(phone: str) -> None:
    with db() as conn:
        conn.execute("DELETE FROM admin_login_attempts WHERE phone = ?", (phone,))


@router.get("/metrics")
def metrics(_: None = Header(default=None), x_admin_token: str | None = Header(default=None)):
    require_admin(x_admin_token)
    with db() as conn:
        users = conn.execute("SELECT COUNT(*) AS c FROM users").fetchone()["c"]
        decodes = conn.execute("SELECT COUNT(*) AS c FROM decodes").fetchone()["c"]
        paid = conn.execute("SELECT COUNT(*) AS c FROM decodes WHERE paid_output IS NOT NULL").fetchone()["c"]
        copies = conn.execute("SELECT COUNT(*) AS c FROM copy_events").fetchone()["c"]
        contacts = conn.execute("SELECT COUNT(*) AS c FROM contacts").fetchone()["c"]
        referrals = conn.execute("SELECT COUNT(*) AS c FROM users WHERE referred_by_user_id IS NOT NULL").fetchone()["c"]
        total_credits = conn.execute("SELECT COALESCE(SUM(credit_balance), 0) AS s FROM users").fetchone()["s"]
        verified_payments = conn.execute("SELECT COUNT(*) AS c FROM payments WHERE status = 'verified'").fetchone()["c"]
        revenue = conn.execute("SELECT COALESCE(SUM(amount), 0) AS s FROM payments WHERE status = 'verified'").fetchone()["s"]
        sms_sent = conn.execute("SELECT COUNT(*) AS c FROM sms_send_logs WHERE status = 'sent'").fetchone()["c"]
        sms_failed = conn.execute("SELECT COUNT(*) AS c FROM sms_send_logs WHERE status = 'failed'").fetchone()["c"]
        by_lens = [dict(row) for row in conn.execute("SELECT dominant_lens, COUNT(*) AS count FROM decodes GROUP BY dominant_lens")]
        safety = [dict(row) for row in conn.execute("SELECT safety_label, COUNT(*) AS count FROM messages GROUP BY safety_label")]
    conversion = paid / decodes if decodes else 0
    copy_rate = copies / paid if paid else 0
    return {
        "users": users,
        "free_decodes": decodes,
        "paid_decodes": paid,
        "revenue": revenue,
        "verified_payments": verified_payments,
        "sms_sent": sms_sent,
        "sms_failed": sms_failed,
        "contacts": contacts,
        "referrals": referrals,
        "total_credits": total_credits,
        "conversion": conversion,
        "copy_rate": copy_rate,
        "by_lens": by_lens,
        "safety": safety,
        "retention": retention_metrics(),
        "frequency": usage_frequency(),
    }


@router.get("/users", response_model=AdminUserListOut)
def user_listing(
    q: str | None = None,
    limit: int = Query(default=50, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    x_admin_token: str | None = Header(default=None),
) -> AdminUserListOut:
    require_admin(x_admin_token)
    filters: list[str] = []
    params: list[str | int] = []
    if q:
        filters.append("(u.phone LIKE ? OR u.id LIKE ? OR u.telegram_id LIKE ? OR u.referral_code LIKE ?)")
        like = f"%{q}%"
        params.extend([like, like, like, like])
    where = f"WHERE {' AND '.join(filters)}" if filters else ""
    with db() as conn:
        total = conn.execute(f"SELECT COUNT(*) AS c FROM users u {where}", params).fetchone()["c"]
        rows = conn.execute(
            f"""
            SELECT
                u.id,
                u.phone,
                u.telegram_id,
                u.created_at,
                u.credit_balance,
                u.source_channel,
                u.referral_code,
                u.referred_by_user_id,
                (SELECT COUNT(*) FROM users ru WHERE ru.referred_by_user_id = u.id) AS referral_count,
                (SELECT COUNT(*) FROM messages m WHERE m.user_id = u.id) AS decodes_count,
                (
                    SELECT COUNT(*)
                    FROM decodes d
                    JOIN messages m ON m.id = d.message_id
                    WHERE m.user_id = u.id AND d.paid_output IS NOT NULL
                ) AS paid_decodes_count,
                (SELECT COUNT(*) FROM contacts c WHERE c.user_id = u.id) AS contacts_count
            FROM users u
            {where}
            ORDER BY u.created_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
    return AdminUserListOut(
        total=int(total),
        limit=limit,
        offset=offset,
        items=[
            AdminUserItem(
                id=row["id"],
                phone=row["phone"],
                telegram_id=row["telegram_id"],
                created_at=row["created_at"],
                credit_balance=int(row["credit_balance"]),
                source_channel=row["source_channel"],
                referral_code=row["referral_code"],
                referred_by_user_id=row["referred_by_user_id"],
                referral_count=int(row["referral_count"]),
                decodes_count=int(row["decodes_count"]),
                paid_decodes_count=int(row["paid_decodes_count"]),
                contacts_count=int(row["contacts_count"]),
            )
            for row in rows
        ],
    )


@router.post("/credits/grant", response_model=AdminGrantCreditsOut)
def grant_credits(payload: AdminGrantCreditsIn, x_admin_token: str | None = Header(default=None)) -> AdminGrantCreditsOut:
    require_admin(x_admin_token)
    if not payload.user_id and not payload.phone:
        raise HTTPException(status_code=400, detail="user_id or phone is required")
    with db() as conn:
        if payload.user_id:
            user = conn.execute("SELECT id FROM users WHERE id = ?", (payload.user_id,)).fetchone()
        else:
            phones = phone_variants(payload.phone)
            placeholders = ",".join("?" for _ in phones)
            user = conn.execute(f"SELECT id FROM users WHERE phone IN ({placeholders})", phones).fetchone() if phones else None
        if not user:
            raise HTTPException(status_code=404, detail="User not found")
        conn.execute("UPDATE users SET credit_balance = credit_balance + ? WHERE id = ?", (payload.credits, user["id"]))
        balance = conn.execute("SELECT credit_balance FROM users WHERE id = ?", (user["id"],)).fetchone()["credit_balance"]
    return AdminGrantCreditsOut(user_id=user["id"], credit_balance=int(balance))


@router.post("/credits/grant-all", response_model=AdminBulkGrantCreditsOut)
def grant_all_credits(payload: AdminBulkGrantCreditsIn, x_admin_token: str | None = Header(default=None)) -> AdminBulkGrantCreditsOut:
    require_admin(x_admin_token)
    with db() as conn:
        result = conn.execute("UPDATE users SET credit_balance = credit_balance + ?", (payload.credits,))
        updated = result.rowcount if result.rowcount is not None else 0
    return AdminBulkGrantCreditsOut(updated_users=int(updated))


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


@router.get("/activity", response_model=AdminActivityListOut)
def activity_listing(
    q: str | None = None,
    user_id: str | None = None,
    limit: int = Query(default=80, ge=1, le=200),
    offset: int = Query(default=0, ge=0),
    x_admin_token: str | None = Header(default=None),
) -> AdminActivityListOut:
    require_admin(x_admin_token)
    params: list[str | int | None] = []
    where: list[str] = []
    if user_id:
        where.append("activity.user_id = ?")
        params.append(user_id)
    if q:
        like = f"%{q}%"
        where.append(
            "(activity.phone LIKE ? OR activity.user_id LIKE ? OR activity.event_type LIKE ? OR activity.title LIKE ? OR activity.detail LIKE ?)"
        )
        params.extend([like, like, like, like, like])
    filter_sql = f"WHERE {' AND '.join(where)}" if where else ""
    base_sql = """
        WITH activity AS (
            SELECT
                'signup:' || u.id AS id,
                u.id AS user_id,
                u.phone AS phone,
                'signup' AS event_type,
                'ثبت‌نام کاربر' AS title,
                'کانال: ' || COALESCE(u.source_channel, 'web') || ' | اعتبار: ' || u.credit_balance AS detail,
                u.source_channel AS status,
                u.created_at AS created_at
            FROM users u

            UNION ALL

            SELECT
                'free:' || m.id AS id,
                m.user_id AS user_id,
                u.phone AS phone,
                'free_decode' AS event_type,
                'تحلیل رایگان' AS title,
                'رابطه: ' || m.relationship_type || ' | هدف: ' || m.user_goal || ' | ایمنی: ' || m.safety_label AS detail,
                m.safety_label AS status,
                m.created_at AS created_at
            FROM messages m
            LEFT JOIN users u ON u.id = m.user_id

            UNION ALL

            SELECT
                'paid:' || d.id AS id,
                m.user_id AS user_id,
                u.phone AS phone,
                'paid_decode' AS event_type,
                'تحلیل کامل' AS title,
                'لنز: ' || d.dominant_lens || ' | Prompt: ' || d.prompt_version AS detail,
                d.paid_model_version AS status,
                COALESCE(d.paid_at, d.created_at) AS created_at
            FROM decodes d
            JOIN messages m ON m.id = d.message_id
            LEFT JOIN users u ON u.id = m.user_id
            WHERE d.paid_output IS NOT NULL

            UNION ALL

            SELECT
                'payment:' || p.id AS id,
                p.user_id AS user_id,
                u.phone AS phone,
                'payment' AS event_type,
                'پرداخت' AS title,
                p.package_id || ' | مبلغ: ' || p.amount || ' | اعتبار: ' || p.credits_added AS detail,
                p.status AS status,
                COALESCE(p.verified_at, p.created_at) AS created_at
            FROM payments p
            LEFT JOIN users u ON u.id = p.user_id

            UNION ALL

            SELECT
                'contact:' || c.id AS id,
                c.user_id AS user_id,
                u.phone AS phone,
                'contact' AS event_type,
                'مخاطب ساخته شد' AS title,
                c.name || ' | ' || c.relationship_type AS detail,
                NULL AS status,
                c.created_at AS created_at
            FROM contacts c
            LEFT JOIN users u ON u.id = c.user_id

            UNION ALL

            SELECT
                'copy:' || c.id AS id,
                m.user_id AS user_id,
                u.phone AS phone,
                'copy' AS event_type,
                'کپی پاسخ' AS title,
                c.reply_label AS detail,
                c.reply_text_id AS status,
                c.created_at AS created_at
            FROM copy_events c
            JOIN decodes d ON d.id = c.decode_id
            JOIN messages m ON m.id = d.message_id
            LEFT JOIN users u ON u.id = m.user_id

            UNION ALL

            SELECT
                'feedback:' || f.id AS id,
                m.user_id AS user_id,
                u.phone AS phone,
                'feedback' AS event_type,
                'بازخورد' AS title,
                COALESCE(f.user_rating, '-') || ' | outcome: ' || COALESCE(f.outcome, '-') || ' | regret: ' || COALESCE(CAST(f.regret_score AS TEXT), '-') AS detail,
                COALESCE(f.selected_reply_label, f.favorite_reply_label) AS status,
                f.created_at AS created_at
            FROM feedback f
            JOIN decodes d ON d.id = f.decode_id
            JOIN messages m ON m.id = d.message_id
            LEFT JOIN users u ON u.id = m.user_id
        )
    """
    with db() as conn:
        total = conn.execute(f"{base_sql} SELECT COUNT(*) AS c FROM activity {filter_sql}", params).fetchone()["c"]
        rows = conn.execute(
            f"""
            {base_sql}
            SELECT *
            FROM activity
            {filter_sql}
            ORDER BY created_at DESC
            LIMIT ? OFFSET ?
            """,
            [*params, limit, offset],
        ).fetchall()
    return AdminActivityListOut(
        total=int(total),
        limit=limit,
        offset=offset,
        items=[
            AdminActivityItem(
                id=row["id"],
                user_id=row["user_id"],
                phone=row["phone"],
                event_type=row["event_type"],
                title=row["title"],
                detail=row["detail"],
                status=row["status"],
                created_at=row["created_at"],
            )
            for row in rows
        ],
    )


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


@router.get("/backup/db", include_in_schema=False)
def download_db_backup(x_admin_token: str | None = Header(default=None)):
    """Hot backup of the SQLite database — streams a byte-perfect copy."""
    require_admin(x_admin_token)
    from app.database import _sqlite_path

    db_path = _sqlite_path()

    def _stream():
        tmp = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        tmp_path = tmp.name
        tmp.close()
        try:
            with sqlite3.connect(db_path) as src:
                with sqlite3.connect(tmp_path) as dst:
                    src.backup(dst)
            with open(tmp_path, "rb") as f:
                while chunk := f.read(65536):
                    yield chunk
        finally:
            os.unlink(tmp_path)

    filename = f"message_decoder_backup_{date.today().isoformat()}.db"
    return StreamingResponse(
        _stream(),
        media_type="application/octet-stream",
        headers={"Content-Disposition": f'attachment; filename="{filename}"'},
    )


def _preview(value: str | None, max_length: int = 180) -> str | None:
    if not value:
        return None
    clean = " ".join(value.split())
    if len(clean) <= max_length:
        return clean
    return f"{clean[:max_length - 1]}…"
