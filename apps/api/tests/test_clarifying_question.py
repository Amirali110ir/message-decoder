"""Tests for T2.4 — a single targeted question when confidence is low and no
episode context was supplied. Question is the last resort, not the first."""

from app.schemas import FreeDecodeIn
from app.services.rule_engine import classify, clarifying_question


def _q(message, **kw):
    payload = FreeDecodeIn(message_text=message, relationship_type="romantic", **kw)
    return clarifying_question(classify(payload), payload), classify(payload)


def test_low_confidence_ambiguous_message_gets_a_question():
    q, c = _q("باشه.", user_goal="calm_conflict")
    assert c.confidence == "پایین"
    assert q is not None and len(q) > 0


def test_strong_signal_message_gets_no_question():
    # Clear oxytocin signal -> high enough confidence -> no question.
    q, c = _q("چرا سرد شدی؟ انگار دیگه دوستم نداری و برات مهم نیستم.", user_goal="calm_conflict")
    assert c.confidence in {"متوسط", "بالا"}
    assert q is None


def test_no_question_when_episode_context_is_provided():
    payload = FreeDecodeIn(
        message_text="باشه.",
        relationship_type="romantic",
        user_goal="calm_conflict",
        episode_background="دیشب سرِ یه موضوع کوچیک بحثمون شد",
    )
    c = classify(payload)
    assert c.confidence == "پایین"  # message itself is still ambiguous
    assert clarifying_question(c, payload) is None  # but we already have context


def test_no_question_in_safety_mode():
    payload = FreeDecodeIn(
        message_text="پیدات میکنم میزنمت",
        relationship_type="romantic",
    )
    c = classify(payload)
    assert c.safety_label == "high_risk"
    assert clarifying_question(c, payload) is None


def test_question_is_tailored_to_dominant_lens():
    payload = FreeDecodeIn(message_text="باشه.", relationship_type="romantic", user_goal="calm_conflict")
    c = classify(payload)
    # romantic + low signal falls back to oxytocin
    assert c.dominant_lens == "oxytocin"
    assert "قبلش" in clarifying_question(c, payload)
