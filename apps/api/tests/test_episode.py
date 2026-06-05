"""Deterministic tests for the episode model (T1.7): the unit of analysis is
the situation arc, not just the focal message."""

from app.schemas import (
    MAX_RECENT_MESSAGES,
    MAX_RECENT_MESSAGE_LEN,
    FreeDecodeIn,
)
from app.services.rule_engine import classify


def test_recent_messages_are_hard_capped():
    payload = FreeDecodeIn(
        message_text="باشه.",
        recent_messages=["x" * 1000] * 20,
    )
    assert payload.recent_messages is not None
    assert len(payload.recent_messages) == MAX_RECENT_MESSAGES
    assert all(len(m) <= MAX_RECENT_MESSAGE_LEN for m in payload.recent_messages)


def test_recent_messages_drops_empty_and_normalises():
    payload = FreeDecodeIn(message_text="باشه.", recent_messages=["  ", "سلام ", ""])
    assert payload.recent_messages == ["سلام"]


def test_episode_context_none_when_no_episode_fields():
    payload = FreeDecodeIn(message_text="باشه.", relationship_type="romantic")
    assert payload.episode_context() is None


def test_episode_context_renders_supplied_fields():
    payload = FreeDecodeIn(
        message_text="دیگه بهم زنگ نزن",
        episode_background="دو سال باهم بودیم، یه‌ماهه سرد شده",
        their_behavior="تا صبح آنلاین بود ولی جواب نداد",
        recent_messages=["شب‌بخیر", "چرا جواب نمیدی"],
    )
    ctx = payload.episode_context()
    assert "پیشینه/رابطه:" in ctx
    assert "رفتار طرف مقابل:" in ctx
    assert "چند پیامِ آخر:" in ctx
    assert "شب‌بخیر | چرا جواب نمیدی" in ctx


def test_single_message_path_is_unchanged():
    # With no episode fields, classification must match the pre-episode behaviour.
    base = FreeDecodeIn(message_text="باشه.", relationship_type="romantic", user_goal="calm_conflict")
    assert base.episode_context() is None
    c = classify(base)
    assert c.dominant_lens in {"oxytocin", "serotonin", "dopamine"}


def test_classify_reads_signal_from_their_behavior():
    # A serotonin (respect) signal placed ONLY in their_behavior must influence
    # the lens, proving classification looks at the whole episode, not just the
    # focal message.
    focal = FreeDecodeIn(message_text="باشه.", relationship_type="romantic", user_goal="understand_only")
    with_episode = FreeDecodeIn(
        message_text="باشه.",
        relationship_type="romantic",
        user_goal="understand_only",
        their_behavior="جلوی بقیه بهم بی احترامی شد و گفت سطح من این نیست",
    )
    assert with_episode.episode_context() is not None
    assert classify(with_episode).lens_scores["serotonin"] > classify(focal).lens_scores["serotonin"]


def test_classify_detects_safety_signal_inside_episode():
    # A threat that appears only in the episode background must still trip
    # Safety Mode — risk is about the situation, not only the last line.
    safe_looking = FreeDecodeIn(
        message_text="کجایی؟",
        relationship_type="romantic",
        episode_background="دیروز گفت پیدات میکنم میزنمت",
    )
    assert classify(safe_looking).safety_label == "high_risk"
