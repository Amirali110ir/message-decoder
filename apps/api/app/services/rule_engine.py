from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any

from app.schemas import FreeDecodeIn
from app.services.rule_catalog import (
    LENS_RULES,
    MANIPULATION_TERMS,
    RELATIONSHIP_PLAYBOOKS,
    RULE_CATALOG_VERSION,
    SAFETY_RULES,
    TONE_RULES,
    USER_GOAL_PLAYBOOKS,
)

from app.utils import normalize_persian

RULE_ENGINE_VERSION = "rule-engine-v0.4"

LENS_TERMS = {
    lens: [*rule["strong_signals"], *rule["weak_signals"]]
    for lens, rule in LENS_RULES.items()
}


@dataclass
class Classification:
    safety_label: str
    dominant_lens: str
    secondary_lenses: list[str]
    confidence: str
    manipulative: bool = False
    tones: list[str] = field(default_factory=list)
    hidden_need: str = ""
    main_risk: str = ""
    recommended_direction: str = ""
    alternative_interpretation: str = ""
    words_to_avoid: list[str] = field(default_factory=list)
    reply_strategy: list[str] = field(default_factory=list)
    safety_reasons: list[str] = field(default_factory=list)
    evidence_terms: list[str] = field(default_factory=list)
    lens_scores: dict[str, float] = field(default_factory=dict)


def classify(payload: FreeDecodeIn) -> Classification:
    # Analyse the whole situation arc (episode), not just the last message, so
    # lens / tone / risk reflect the build-up rather than one isolated line.
    episode = payload.episode_context()
    raw_text = "\n".join(
        part for part in (payload.message_text, payload.optional_context, episode) if part
    )
    text = normalize_persian(raw_text).lower()
    safety_reasons = _matched_categories(text, SAFETY_RULES)
    tones = _matched_categories(text, TONE_RULES)
    if safety_reasons:
        return Classification(
            "high_risk",
            "serotonin",
            [],
            "بالا",
            tones=tones,
            hidden_need="اولویت این پیام احتمالاً فهم رابطه نیست؛ اولویت حفظ امنیت، مرزبندی و کم کردن ریسک است.",
            main_risk="پاسخ احساسی، تحریک‌کننده یا طولانی می‌تواند خطر را بیشتر کند.",
            recommended_direction="کوتاه، روشن، بدون تحریک بیشتر مرز بگذار و اگر خطر جدی است از فرد قابل اعتماد یا مرجع مناسب کمک بگیر.",
            alternative_interpretation="ممکن است بخشی از پیام از خشم لحظه‌ای آمده باشد، اما وجود نشانه‌های خطر باید جدی گرفته شود.",
            words_to_avoid=["تهدید متقابل", "طعنه", "دعوت به حضوری حرف زدن", "افشای اطلاعات بیشتر"],
            reply_strategy=["safety_first", "short_boundary", "document_if_needed"],
            safety_reasons=safety_reasons,
        )

    manipulative = any(_term_active_in_text(text, term) for term in MANIPULATION_TERMS)
    scores = _lens_scores(text)
    _apply_context_bias(scores, payload, tones)
    dominant = max(scores, key=scores.get)
    if scores[dominant] <= 0:
        dominant = "oxytocin" if payload.relationship_type in ("romantic", "ex", "family") else "dopamine"

    secondary = [
        key
        for key, value in sorted(scores.items(), key=lambda item: item[1], reverse=True)
        if key != dominant and value > 0
    ]
    profile = lens_profile(dominant, payload.relationship_type, payload.user_goal, manipulative)
    return Classification(
        "manipulation_redirect" if manipulative else "normal",
        dominant,
        secondary,
        _confidence_from_score(scores[dominant]),
        manipulative,
        tones=tones or default_tones(payload.relationship_type, payload.user_goal),
        hidden_need=profile["hidden_need"],
        main_risk=profile["main_risk"],
        recommended_direction=profile["recommended_direction"],
        alternative_interpretation=profile["alternative_interpretation"],
        words_to_avoid=profile["words_to_avoid"],
        reply_strategy=profile["reply_strategy"],
        evidence_terms=matched_terms(text, LENS_TERMS[dominant]),
        lens_scores=scores,
    )


def _confidence_from_score(score: float) -> str:
    """Three-tier confidence so genuinely ambiguous messages are flagged.

    A bare message with no lens keyword falls back to a default lens with a tiny
    context bias (<0.8) — that is exactly the "پایین" case where a targeted
    clarifying question beats a blind analysis (T2.4).
    """
    if score >= 2:
        return "بالا"
    if score >= 0.8:
        return "متوسط"
    return "پایین"


# A single targeted question per dominant lens, mapped to the missing episode
# piece. The aim is to recover the situation arc with ONE question, not a form.
_CLARIFYING_QUESTIONS = {
    "oxytocin": "قبلش چی شده بود؟ دعوا کرده بودید یا یهویی این پیامو داد؟",
    "serotonin": "قبلش اتفاقی افتاد که حس کنه بهش بی‌احترامی شده یا کم گرفتیش؟",
    "dopamine": "این پیام سرِ یه موضوعِ مشخصه؟ چیزی بوده که ازت می‌خواسته و عقب افتاده؟",
}
_CLARIFYING_DEFAULT = "قبلش چی شده بود؟ یه‌کم از ماجرا بگو تا دقیق‌تر بخونمش."


def clarifying_question(classification: Classification, payload: FreeDecodeIn) -> str | None:
    """Return ONE targeted question when confidence is low and no episode was given.

    Question is the last resort, not the first: it only fires for genuinely
    ambiguous input (low confidence) where the user has not already supplied any
    episode context. Once they answer (episode present) or the signal is strong
    enough, no question is asked. Never asks in Safety Mode.
    """
    if classification.safety_label == "high_risk":
        return None
    if classification.confidence != "پایین":
        return None
    if payload.episode_context() is not None:
        return None
    return _CLARIFYING_QUESTIONS.get(classification.dominant_lens, _CLARIFYING_DEFAULT)


def classification_payload(classification: Classification) -> dict[str, Any]:
    return {
        "rule_catalog_version": RULE_CATALOG_VERSION,
        "rule_engine_version": RULE_ENGINE_VERSION,
        "safety_label": classification.safety_label,
        "safety_reasons": classification.safety_reasons,
        "dominant_lens": classification.dominant_lens,
        "secondary_lenses": classification.secondary_lenses,
        "confidence": classification.confidence,
        "manipulative": classification.manipulative,
        "tones": classification.tones,
        "hidden_need": classification.hidden_need,
        "main_risk": classification.main_risk,
        "recommended_direction": classification.recommended_direction,
        "alternative_interpretation": classification.alternative_interpretation,
        "words_to_avoid": classification.words_to_avoid,
        "reply_strategy": classification.reply_strategy,
        "evidence_terms": classification.evidence_terms,
        "lens_scores": classification.lens_scores,
    }


def paid_reply_playbook(relationship_type: str, user_goal: str, dominant_lens: str) -> dict[str, Any]:
    relationship_playbook = RELATIONSHIP_PLAYBOOKS.get(relationship_type, RELATIONSHIP_PLAYBOOKS["unknown"])
    goal_playbook = USER_GOAL_PLAYBOOKS.get(user_goal, USER_GOAL_PLAYBOOKS["understand_only"])
    base: dict[str, Any] = {
        "rule_catalog_version": RULE_CATALOG_VERSION,
        "rule_engine_version": RULE_ENGINE_VERSION,
        "must_include": relationship_playbook["must_include"],
        "relationship_playbook": relationship_playbook,
        "user_goal_playbook": goal_playbook,
        "priority": goal_playbook["priority"],
        "copy_ready_rule": "نسخه قابل کپی باید بهترین تعادل بین هدف کاربر، لنز غالب و کم کردن ریسک مکالمه باشد.",
        "avoid": ["تشخیص قطعی نیت", "برچسب روانشناختی", "طعنه", "التماس", "تهدید", "گناه‌دادن"],
    }
    if dominant_lens == "dopamine":
        base["core_moves"] = ["پذیرش سهم مشخص", "اقدام بعدی روشن", "زمان‌بندی دقیق", "کاهش ابهام"]
    elif dominant_lens == "serotonin":
        base["core_moves"] = ["برگرداندن احترام", "پذیرش سهم آسیب", "مرز بدون تحقیر", "پرهیز از جنگ برتری"]
    else:
        base["core_moves"] = ["دیدن احساس", "روشن کردن نیت", "دعوت به بیان مستقیم", "پرهیز از سردی یا دفاع طولانی"]
    base["style"] = relationship_playbook["style"]
    return base


def lens_profile(lens: str, relationship_type: str, user_goal: str, manipulative: bool) -> dict[str, Any]:
    source = LENS_RULES[lens]
    profile = {
        "hidden_need": source["hidden_need"],
        "main_risk": source["main_risk"],
        "recommended_direction": source["recommended_direction"],
        "alternative_interpretation": source["alternative_interpretation"],
        "words_to_avoid": list(source["words_to_avoid"]),
        "reply_strategy": list(source["reply_strategy"]),
    }
    if relationship_type == "ex":
        profile["reply_strategy"] = [*profile["reply_strategy"], "no_reopening_unless_intended", "warm_boundary"]
        profile["words_to_avoid"] = [*profile["words_to_avoid"], "دلم برات تنگ شده اگه مطمئن نیستی", "برگرد"]
    if relationship_type in ("manager_colleague", "customer") or user_goal == "professional_reply":
        profile["reply_strategy"] = ["professional", "concise", "accountability", "specific_next_step", "no_emotional_overexplain"]
    if user_goal == "end_conversation":
        profile["reply_strategy"] = [*profile["reply_strategy"], "ending_line"]
    if manipulative:
        profile["hidden_need"] = "درخواست کاربر رنگ کنترل یا فشار روانی دارد؛ نیاز سالم‌تر احتمالاً بیان احساس، مرز یا خواسته بدون دستکاری طرف مقابل است."
        profile["main_risk"] = "اگر پاسخ برای ایجاد حس گناه یا کنترل ساخته شود، رابطه ناسالم‌تر و پرتنش‌تر می‌شود."
        profile["recommended_direction"] = "درخواست را به پیام قاطع، بالغ و غیرتحقیرآمیز تبدیل کن که احساس و مرز را واضح منتقل کند."
        profile["reply_strategy"] = ["manipulation_redirect", "assertive", "no_guilt_trip", "healthy_boundary"]
    return profile


def default_tones(relationship_type: str, user_goal: str) -> list[str]:
    if relationship_type in ("manager_colleague", "customer") or user_goal == "professional_reply":
        return ["رسمی"]
    if relationship_type == "ex" or user_goal in ("set_boundary", "end_conversation"):
        return ["تعیین‌کننده مرز روابط"]
    return ["مبهم"]


def matched_terms(text: str, terms: list[str]) -> list[str]:
    return [term for term in terms if term.lower() in text][:8]


def _lens_scores(text: str) -> dict[str, float]:
    return {
        lens: _weighted_score(text, rule["strong_signals"], rule["weak_signals"])
        for lens, rule in LENS_RULES.items()
    }


def _weighted_score(text: str, strong_terms: list[str], weak_terms: list[str]) -> float:
    strong = sum(1 for term in strong_terms if term.lower() in text)
    weak = sum(1 for term in weak_terms if term.lower() in text)
    return strong + (weak * 0.4)


def _term_active_in_text(text: str, term: str) -> bool:
    """Return True only if term appears in text without an immediate نمی negation prefix.

    Persian verbs starting with می can be negated by prepending ن, forming نمی.
    «میکشمت» is a substring of «نمیکشمت», so a raw `in` check produces a false
    positive. We walk every occurrence and accept it only when the char immediately
    before is not ن (or when the term doesn't start with می, where this isn't needed).
    """
    t = term.lower()
    if not t.startswith("می"):
        return t in text
    idx = text.find(t)
    while idx != -1:
        if idx == 0 or text[idx - 1] != "ن":
            return True
        idx = text.find(t, idx + 1)
    return False


def _matched_categories(text: str, catalog: dict[str, list[str]]) -> list[str]:
    return [label for label, terms in catalog.items() if any(_term_active_in_text(text, term) for term in terms)]


def _apply_context_bias(scores: dict[str, float], payload: FreeDecodeIn, tones: list[str]) -> None:
    if payload.relationship_type in ("romantic", "ex", "family"):
        scores["oxytocin"] += 0.35
    if payload.relationship_type in ("manager_colleague", "customer"):
        scores["dopamine"] += 0.25
        scores["serotonin"] += 0.25
    goal_bias = {
        "professional_reply": "dopamine",
        "make_them_accountable": "dopamine",
        "avoid_needy": "oxytocin",
        "end_conversation": "serotonin",
    }.get(payload.user_goal)
    if goal_bias:
        scores[goal_bias] += 0.5
    if payload.user_goal == "set_boundary":
        scores["serotonin"] += 0.25
    if "کنترل‌گر" in tones:
        scores["dopamine"] += 0.75
    if "تحقیرکننده" in tones or "سرزنش‌گر" in tones:
        scores["serotonin"] += 0.75
    if "گناه‌دهنده" in tones or "قربانی‌گونه" in tones:
        scores["oxytocin"] += 0.5
