from __future__ import annotations

import sqlite3
from collections import Counter
from typing import Any

from app.database import db
from app.schemas import FreeDecodeIn
from app.services.rule_engine import RULE_ENGINE_VERSION, classify, paid_reply_playbook


EVAL_CASES = [
    {
        "id": "romantic_late_seen",
        "message_text": "چرا اینقدر دیر سین می‌کنی؟ همش آنلاینی ولی جواب منو نمیدی. اگه مزاحمم بگو.",
        "relationship_type": "romantic",
        "user_goal": "calm_conflict",
        "expected_lens": "oxytocin",
        "expected_tones": ["قربانی‌گونه", "منفعل-پرخاشگر"],
    },
    {
        "id": "work_deadline_pressure",
        "message_text": "گزارش چی شد؟ قرار بود تا ظهر دست من باشه. چرا کارا اینقدر کند پیش میره؟",
        "relationship_type": "manager_colleague",
        "user_goal": "professional_reply",
        "expected_lens": "dopamine",
        "expected_tones": ["تند"],
    },
    {
        "id": "work_credit_status",
        "message_text": "فکر کنم یادت رفت بگی که این ایده رو من تو جلسه قبل مطرح کرده بودم. جالب بود که به اسم خودت تموم شد.",
        "relationship_type": "manager_colleague",
        "user_goal": "calm_conflict",
        "expected_lens": "serotonin",
        "expected_tones": ["منفعل-پرخاشگر", "کنایه‌آمیز"],
    },
    {
        "id": "ex_breadcrumb",
        "message_text": "دیشب خوابتو دیدم. خیلی دلم گرفت. کاش می‌شد همه چی رو درست کرد...",
        "relationship_type": "ex",
        "user_goal": "avoid_needy",
        "expected_lens": "oxytocin",
        "expected_tones": ["غمگین", "مبهم"],
    },
    {
        "id": "family_guilt_call",
        "message_text": "معلوم هست کجایی؟ سالی یه بار هم یه زنگ به ما نمی‌زنی. کلا ما رو فراموش کردی رفت پی کارش.",
        "relationship_type": "family",
        "user_goal": "improve_relationship",
        "expected_lens": "oxytocin",
        "expected_tones": ["قربانی‌گونه", "منفعل-پرخاشگر"],
    },
    {
        "id": "customer_insult",
        "message_text": "من پول ندادم که این آشغال رو تحویلم بدید! واقعا خجالت نمی‌کشید با این پشتیبانی‌تون؟",
        "relationship_type": "customer",
        "user_goal": "professional_reply",
        "expected_lens": "serotonin",
        "expected_tones": ["تند", "تحقیرکننده"],
    },
    {
        "id": "romantic_control_threat",
        "message_text": "حق نداری با اون آدم بری بیرون. من خوشم نمیاد ازش. اگه رفتی دیگه به من پیام نده.",
        "relationship_type": "romantic",
        "user_goal": "set_boundary",
        "expected_lens": "dopamine",
        "expected_tones": ["کنترل‌گر", "تهدیدکننده"],
    },
    {
        "id": "family_comparison",
        "message_text": "ببین پسرخاله‌ات همسن توئه، ماشین خریده، خونه خریده. تو هنوز داری درجا می‌زنی. یکم به خودت بیا.",
        "relationship_type": "family",
        "user_goal": "set_boundary",
        "expected_lens": "serotonin",
        "expected_tones": ["تحقیرکننده"],
    },
    {
        "id": "unknown_job_scam",
        "message_text": "سلام یه پیشنهاد کاری فوق‌العاده با درآمد دلاری براتون دارم. شمارتون رو بذارید تماس بگیرم.",
        "relationship_type": "unknown",
        "user_goal": "understand_only",
        "expected_lens": "dopamine",
        "expected_tones": ["رسمی", "تعیین‌کننده مرز روابط"],
    },
    {
        "id": "customer_status_attack",
        "message_text": "شما اصلا می‌دونید من کی هستم که اینطوری با من حرف می‌زنید؟ مدیرتون رو صدا کنید!",
        "relationship_type": "customer",
        "user_goal": "calm_conflict",
        "expected_lens": "serotonin",
        "expected_tones": ["تند"],
    },
    {
        "id": "blackmail_safety",
        "message_text": "اگه پول ندی عکستو پخش میکنم و آبروتو میبرم.",
        "relationship_type": "unknown",
        "user_goal": "calm_conflict",
        "expected_lens": "serotonin",
        "expected_safety_label": "high_risk",
        "expected_tones": ["تهدیدکننده"],
    },
    {
        "id": "manipulation_redirect",
        "message_text": "چی بگم که عذاب وجدان بگیره و به پام بیفته؟",
        "relationship_type": "ex",
        "user_goal": "make_them_accountable",
        "expected_lens": "dopamine",
        "expected_safety_label": "manipulation_redirect",
        "expected_tones": [],
    },
    {
        "id": "romantic_boundary_tone",
        "message_text": "با این لحن با من حرف نزن.",
        "relationship_type": "romantic",
        "user_goal": "set_boundary",
        "expected_lens": "serotonin",
        "expected_tones": ["تعیین‌کننده مرز روابط", "تند"],
    },
    {
        "id": "unknown_location_threat",
        "message_text": "لوکیشنتو بفرست، وگرنه خودم می‌فهمم کجایی.",
        "relationship_type": "unknown",
        "user_goal": "end_conversation",
        "expected_lens": "serotonin",
        "expected_safety_label": "high_risk",
        "expected_tones": ["تهدیدکننده", "کنترل‌گر"],
    },
    {
        "id": "work_contract_risk",
        "message_text": "لطفاً تا روشن شدن قرارداد هیچ تعهدی به مشتری ندهید.",
        "relationship_type": "manager_colleague",
        "user_goal": "professional_reply",
        "expected_lens": "dopamine",
        "expected_tones": ["رسمی", "تعیین‌کننده مرز روابط"],
    },
    {
        "id": "romantic_clarity_pressure",
        "message_text": "من فقط یه جواب روشن می‌خوام: هستی یا نه؟",
        "relationship_type": "romantic",
        "user_goal": "avoid_needy",
        "expected_lens": "dopamine",
        "expected_tones": ["تند", "تعیین‌کننده مرز روابط"],
    },
    {
        "id": "family_money_accountability",
        "message_text": "پول را که می‌گیری یادت هست، ولی وقتی باید پس بدهی نه.",
        "relationship_type": "family",
        "user_goal": "make_them_accountable",
        "expected_lens": "serotonin",
        "expected_tones": ["کنایه‌آمیز", "تند"],
    },
    {
        "id": "customer_trust_loss",
        "message_text": "با توجه به تجربه اخیر، اعتماد من به تیم شما به‌شدت کاهش پیدا کرده است.",
        "relationship_type": "customer",
        "user_goal": "improve_relationship",
        "expected_lens": "oxytocin",
        "expected_tones": ["رسمی", "سرد"],
    },
]


def evaluate_rule_engine() -> dict[str, Any]:
    results: list[dict[str, Any]] = []
    lens_hits = 0
    safety_hits = 0
    tone_expected = 0
    tone_hits = 0
    misses: list[dict[str, Any]] = []
    lens_confusion: Counter[str] = Counter()

    for case in EVAL_CASES:
        payload = FreeDecodeIn(
            message_text=case["message_text"],
            relationship_type=case["relationship_type"],
            user_goal=case["user_goal"],
            privacy_consent="none",
        )
        classification = classify(payload)
        expected_safety = case.get("expected_safety_label", "normal")
        lens_ok = classification.dominant_lens == case["expected_lens"]
        safety_ok = classification.safety_label == expected_safety
        expected_tones = set(case.get("expected_tones", []))
        actual_tones = set(classification.tones)
        missing_tones = sorted(expected_tones - actual_tones)
        tone_expected += len(expected_tones)
        tone_hits += len(expected_tones & actual_tones)
        lens_hits += int(lens_ok)
        safety_hits += int(safety_ok)
        if not lens_ok:
            lens_confusion[f"{case['expected_lens']}->{classification.dominant_lens}"] += 1
        row = {
            "id": case["id"],
            "lens_ok": lens_ok,
            "safety_ok": safety_ok,
            "expected_lens": case["expected_lens"],
            "actual_lens": classification.dominant_lens,
            "expected_safety_label": expected_safety,
            "actual_safety_label": classification.safety_label,
            "expected_tones": sorted(expected_tones),
            "actual_tones": classification.tones,
            "missing_tones": missing_tones,
            "lens_scores": classification.lens_scores,
            "evidence_terms": classification.evidence_terms,
            "playbook_must_include": paid_reply_playbook(
                case["relationship_type"], case["user_goal"], classification.dominant_lens
            )["must_include"],
        }
        results.append(row)
        if not lens_ok or not safety_ok or missing_tones:
            misses.append(row)

    total = len(EVAL_CASES)
    metrics = {
        "case_count": total,
        "lens_accuracy": round(lens_hits / total, 4),
        "safety_accuracy": round(safety_hits / total, 4),
        "tone_recall": round(tone_hits / tone_expected, 4) if tone_expected else 1,
        "lens_confusion": dict(lens_confusion),
    }
    return {
        "rule_engine_version": RULE_ENGINE_VERSION,
        "metrics": metrics,
        "misses": misses,
        "recommendations": _recommend(metrics, misses),
        "results": results,
    }


def candidate_eval_cases(limit: int = 50) -> dict[str, Any]:
    """Return real negative-feedback samples worth turning into eval cases.

    This intentionally does not write new tests or tables. The daily loop can
    review these rows, then a human/dev promotes the best ones into EVAL_CASES.
    """
    safe_limit = min(max(limit, 1), 200)
    negative_ratings = {"bad", "poor", "ضعیف", "بد", "1", "2"}
    negative_outcomes = {"worse", "bad", "regret", "دعوا شد", "بدتر شد", "پشیمون شدم"}
    rows: list[dict[str, Any]] = []

    try:
        with db() as conn:
            feedback_rows = conn.execute(
                """
                SELECT
                    f.id AS feedback_id,
                    f.decode_id,
                    f.user_rating,
                    f.outcome,
                    f.regret_score,
                    f.user_comment,
                    f.created_at,
                    m.raw_text,
                    m.anonymized_text,
                    m.relationship_type,
                    m.user_goal,
                    m.optional_context
                FROM feedback f
                JOIN decodes d ON d.id = f.decode_id
                JOIN messages m ON m.id = d.message_id
                ORDER BY f.created_at DESC
                LIMIT ?
                """,
                (safe_limit * 4,),
            ).fetchall()
    except sqlite3.OperationalError as exc:
        if "no such table" not in str(exc):
            raise
        feedback_rows = []

    for row in feedback_rows:
        rating = (row["user_rating"] or "").strip().lower()
        outcome = (row["outcome"] or "").strip().lower()
        regret_score = row["regret_score"]
        user_comment = (row["user_comment"] or "").strip()
        is_negative = (
            (regret_score is not None and regret_score >= 4)
            or rating in negative_ratings
            or outcome in negative_outcomes
            or bool(user_comment)
        )
        if not is_negative:
            continue

        message_text = row["anonymized_text"] or row["raw_text"] or row["optional_context"] or ""
        if not message_text.strip():
            continue

        payload = FreeDecodeIn(
            message_text=message_text,
            relationship_type=row["relationship_type"],
            user_goal=row["user_goal"],
            optional_context=row["optional_context"],
            privacy_consent="none",
        )
        classification = classify(payload)
        rows.append(
            {
                "feedback_id": row["feedback_id"],
                "decode_id": row["decode_id"],
                "created_at": row["created_at"],
                "message_preview": _preview(message_text),
                "relationship_type": row["relationship_type"],
                "user_goal": row["user_goal"],
                "feedback_signals": {
                    "user_rating": row["user_rating"],
                    "outcome": row["outcome"],
                    "regret_score": regret_score,
                    "user_comment": user_comment or None,
                },
                "current_classification": {
                    "dominant_lens": classification.dominant_lens,
                    "safety_label": classification.safety_label,
                    "tones": classification.tones,
                    "lens_scores": classification.lens_scores,
                    "evidence_terms": classification.evidence_terms,
                },
                "suggested_eval_case": {
                    "message_text": message_text,
                    "relationship_type": row["relationship_type"],
                    "user_goal": row["user_goal"],
                    "expected_lens": classification.dominant_lens,
                    "expected_tones": classification.tones,
                    "expected_safety_label": classification.safety_label,
                    "review_note": "این expectedها خروجی فعلی موتور هستند؛ قبل از promote کردن، با قضاوت انسانی اصلاح شوند.",
                },
            }
        )
        if len(rows) >= safe_limit:
            break

    return {
        "rule_engine_version": RULE_ENGINE_VERSION,
        "candidate_count": len(rows),
        "candidate_cases": rows,
        "selection_rule": "regret_score>=4 یا rating/outcome منفی یا کامنت کاربر؛ بدون نوشتن در دیتابیس.",
    }


def _recommend(metrics: dict[str, Any], misses: list[dict[str, Any]]) -> list[str]:
    recommendations: list[str] = []
    if metrics["lens_accuracy"] < 0.9:
        recommendations.append("دقت لنز زیر ۹۰٪ است؛ strong_signals و context biasهای لنزهای اشتباه را بازبینی کن.")
    if metrics["tone_recall"] < 0.8:
        recommendations.append("tone recall پایین است؛ برای toneهای جاافتاده signalهای محاوره‌ای بیشتری اضافه کن.")
    if metrics["safety_accuracy"] < 1:
        recommendations.append("safety miss وجود دارد؛ safety catalog باید قبل از هر bias دیگری تقویت شود.")
    for miss in misses[:5]:
        if miss["missing_tones"]:
            recommendations.append(f"{miss['id']}: toneهای جاافتاده {', '.join(miss['missing_tones'])} را به catalog اضافه کن.")
        if not miss["lens_ok"]:
            recommendations.append(
                f"{miss['id']}: لنز {miss['expected_lens']} انتظار می‌رفت ولی {miss['actual_lens']} شد؛ scoreها را بررسی کن."
            )
    if not recommendations:
        recommendations.append("eval فعلی سالم است؛ برای ارتقای بعدی caseهای بیشتری از داده واقعی و feedback منفی اضافه کن.")
    return recommendations


def _preview(text: str, limit: int = 180) -> str:
    normalized = " ".join(text.split())
    return normalized if len(normalized) <= limit else f"{normalized[:limit]}..."
