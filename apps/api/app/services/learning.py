from __future__ import annotations

from datetime import datetime, timedelta, timezone
from typing import Any

from app.database import db
from app.utils import dumps, new_id, now_iso


POSITIVE_VALUES = {"good", "great", "positive", "helpful", "resolved", "yes", "خوب", "عالی", "مثبت", "کمک کرد"}
NEGATIVE_VALUES = {"bad", "negative", "unhelpful", "regret", "no", "بد", "منفی", "کمک نکرد"}


def build_daily_learning_report(report_date: str | None = None, persist: bool = False) -> dict[str, Any]:
    start, end, label = _report_window(report_date)
    with db() as conn:
        total_decodes = _count(conn, "SELECT COUNT(*) AS c FROM decodes WHERE created_at >= ? AND created_at < ?", (start, end))
        paid_decodes = _count(
            conn,
            "SELECT COUNT(*) AS c FROM decodes WHERE paid_at IS NOT NULL AND paid_at >= ? AND paid_at < ?",
            (start, end),
        )
        copied_paid = _count(
            conn,
            """
            SELECT COUNT(DISTINCT c.decode_id) AS c
            FROM copy_events c
            JOIN decodes d ON d.id = c.decode_id
            WHERE c.created_at >= ? AND c.created_at < ? AND d.paid_output IS NOT NULL
            """,
            (start, end),
        )
        feedback_rows = [
            dict(row)
            for row in conn.execute(
                """
                SELECT f.user_rating, f.outcome, f.regret_score, d.dominant_lens,
                       COALESCE(d.free_model_version, d.model_version) AS free_model_version,
                       d.paid_model_version, d.prompt_version, d.rule_engine_version
                FROM feedback f
                JOIN decodes d ON d.id = f.decode_id
                WHERE f.created_at >= ? AND f.created_at < ?
                """,
                (start, end),
            )
        ]
        lens_mix = [
            dict(row)
            for row in conn.execute(
                """
                SELECT dominant_lens, COUNT(*) AS count
                FROM decodes
                WHERE created_at >= ? AND created_at < ?
                GROUP BY dominant_lens
                ORDER BY count DESC
                """,
                (start, end),
            )
        ]
        model_mix = [
            dict(row)
            for row in conn.execute(
                """
                SELECT COALESCE(free_model_version, model_version) AS free_model_version,
                       COALESCE(paid_model_version, 'none') AS paid_model_version,
                       prompt_version,
                       COALESCE(rule_engine_version, 'unknown') AS rule_engine_version,
                       COUNT(*) AS count
                FROM decodes
                WHERE created_at >= ? AND created_at < ?
                GROUP BY free_model_version, paid_model_version, prompt_version, rule_engine_version
                ORDER BY count DESC
                """,
                (start, end),
            )
        ]
        safety_mix = [
            dict(row)
            for row in conn.execute(
                """
                SELECT safety_label, COUNT(*) AS count
                FROM messages
                WHERE created_at >= ? AND created_at < ?
                GROUP BY safety_label
                ORDER BY count DESC
                """,
                (start, end),
            )
        ]

    feedback_count = len(feedback_rows)
    positive_feedback = sum(_is_positive(row.get("user_rating")) or _is_positive(row.get("outcome")) for row in feedback_rows)
    negative_feedback = sum(_is_negative(row.get("user_rating")) or _is_negative(row.get("outcome")) for row in feedback_rows)
    regret_scores = [int(row["regret_score"]) for row in feedback_rows if row.get("regret_score") is not None]
    average_regret = round(sum(regret_scores) / len(regret_scores), 2) if regret_scores else None
    copy_rate = copied_paid / paid_decodes if paid_decodes else 0
    positive_feedback_rate = positive_feedback / feedback_count if feedback_count else 0
    negative_feedback_rate = negative_feedback / feedback_count if feedback_count else 0

    metrics = {
        "report_date": label,
        "window_start": start,
        "window_end": end,
        "total_decodes": total_decodes,
        "paid_decodes": paid_decodes,
        "copied_paid_decodes": copied_paid,
        "copy_rate": round(copy_rate, 4),
        "feedback_count": feedback_count,
        "positive_feedback_rate": round(positive_feedback_rate, 4),
        "negative_feedback_rate": round(negative_feedback_rate, 4),
        "average_regret_score": average_regret,
        "lens_mix": lens_mix,
        "safety_mix": safety_mix,
        "model_mix": model_mix,
    }
    recommendations = _recommend(metrics)
    report = {"metrics": metrics, "recommendations": recommendations}
    if persist:
        with db() as conn:
            conn.execute(
                "INSERT INTO daily_learning_reports (id, report_date, metrics, recommendations, created_at) VALUES (?, ?, ?, ?, ?)",
                (new_id("learn"), label, dumps(metrics), dumps(recommendations), now_iso()),
            )
    return report


def record_quality_signal(decode_id: str, signal_name: str, signal_value: str, source: str, weight: float = 1) -> None:
    with db() as conn:
        conn.execute(
            """
            INSERT INTO quality_signals (id, decode_id, signal_name, signal_value, weight, source, created_at)
            VALUES (?, ?, ?, ?, ?, ?, ?)
            """,
            (new_id("sig"), decode_id, signal_name, signal_value, weight, source, now_iso()),
        )


def _report_window(report_date: str | None) -> tuple[str, str, str]:
    if report_date:
        start_dt = datetime.fromisoformat(report_date).replace(tzinfo=timezone.utc)
    else:
        now = datetime.now(timezone.utc)
        start_dt = datetime(now.year, now.month, now.day, tzinfo=timezone.utc) - timedelta(days=1)
    end_dt = start_dt + timedelta(days=1)
    return start_dt.isoformat(), end_dt.isoformat(), start_dt.date().isoformat()


def _count(conn, sql: str, params: tuple[str, ...]) -> int:
    return int(conn.execute(sql, params).fetchone()["c"])


def _is_positive(value: str | None) -> bool:
    return bool(value and value.strip().lower() in POSITIVE_VALUES)


def _is_negative(value: str | None) -> bool:
    return bool(value and value.strip().lower() in NEGATIVE_VALUES)


def _recommend(metrics: dict[str, Any]) -> list[str]:
    recommendations: list[str] = []
    if metrics["total_decodes"] < 30:
        recommendations.append("داده امروز برای تصمیم مدل یا prompt کم است؛ تا حداقل ۳۰ decode فقط مشاهده کن.")
    if metrics["paid_decodes"] and metrics["copy_rate"] < 0.45:
        recommendations.append("copy rate پایین است؛ کیفیت reply_options، طول پاسخ‌ها و label لحن‌ها را بازبینی کن.")
    if metrics["feedback_count"] < max(3, metrics["paid_decodes"] * 0.15):
        recommendations.append("feedback کم جمع شده؛ بعد از copy یا چند دقیقه بعد یک سؤال یک‌کلیکی اضافه کن.")
    if metrics["negative_feedback_rate"] > 0.25:
        recommendations.append("negative feedback بالاست؛ نمونه‌های بد را وارد eval set کن و prompt paid را اصلاح کن.")
    if metrics["average_regret_score"] is not None and metrics["average_regret_score"] >= 4:
        recommendations.append("regret score بالاست؛ پاسخ‌ها احتمالا بیش از حد تند، طولانی یا مطمئن‌اند.")
    if not recommendations:
        recommendations.append("وضعیت امروز نرمال است؛ A/B تست کوچک روی prompt paid یا مدل free اجرا کن.")
    return recommendations
