"""Deterministic (no-network) tests for the paid-quality guardrails:

- cache key sensitivity to prompt version / model (task #3)
- few-shot golden example selection (tasks #5/#6)
- post-generation forbidden-phrase inspector (task #7)
"""

import app.services.ai as ai
from app.services.ai import (
    DEFENSIVE_EXCUSE_PHRASES,
    PSYCH_JARGON_PHRASES,
    PAID_CONTEXT_COMPRESS_THRESHOLD,
    _build_cache_key,
    _paid_reply_texts,
    _should_compress_context,
    find_forbidden_phrases,
)
from app.services.golden_examples import (
    GOLDEN_EXAMPLES,
    select_golden_examples,
)


# ---- cache key sensitivity (task #3) ----

def test_cache_key_is_deterministic():
    up = {"task": "paid_decode", "message_text": "سلام", "x": [1, 2]}
    assert _build_cache_key(up, "model-a") == _build_cache_key(up, "model-a")


def test_cache_key_depends_on_model():
    up = {"task": "paid_decode", "message_text": "سلام"}
    assert _build_cache_key(up, "free-model") != _build_cache_key(up, "paid-model")


def test_cache_key_depends_on_prompt_version(monkeypatch):
    up = {"task": "paid_decode", "message_text": "سلام"}
    monkeypatch.setattr(ai, "PROMPT_VERSION", "v-old")
    k_old = _build_cache_key(up, "m")
    monkeypatch.setattr(ai, "PROMPT_VERSION", "v-new")
    k_new = _build_cache_key(up, "m")
    assert k_old != k_new


# ---- golden examples (tasks #5/#6) ----

def test_golden_examples_cover_both_wedge_goals():
    goals = {ex.user_goal for ex in GOLDEN_EXAMPLES}
    assert {"calm_conflict", "avoid_needy"} <= goals
    assert len(GOLDEN_EXAMPLES) >= 20


def test_golden_examples_have_no_defensive_or_jargon_text():
    for ex in GOLDEN_EXAMPLES:
        for bad in DEFENSIVE_EXCUSE_PHRASES + PSYCH_JARGON_PHRASES:
            assert bad not in ex.reply, f"{ex.id} contains forbidden phrase {bad}"


def test_golden_selection_prefers_matching_goal_and_scopes_to_romantic():
    sel = select_golden_examples("romantic", "avoid_needy", limit=4)
    assert sel and sel[0].user_goal == "avoid_needy"
    assert select_golden_examples("manager_colleague", "calm_conflict") == []


# ---- forbidden-phrase inspector (task #7) ----

def test_inspector_detects_model_words_and_excuses():
    texts = ["می‌فهمم چرا دلخوری.", "راستش سرم شلوغ بود ولی مهمی.", "برگرد لطفا."]
    hits = find_forbidden_phrases(texts, ["برگرد"])
    assert "سرم شلوغ بود" in hits
    assert "برگرد" in hits


def test_inspector_no_false_positive_on_clean_reply():
    assert find_forbidden_phrases(["تو برام مهمی. بیا حرف بزنیم."], []) == []


# ---- context compression threshold (T10.2) ----

def test_short_context_is_not_compressed():
    assert _should_compress_context("یه زمینه‌ی کوتاه") is False
    assert _should_compress_context(None) is False


def test_long_context_triggers_compression():
    assert _should_compress_context("x" * (PAID_CONTEXT_COMPRESS_THRESHOLD + 1)) is True


def test_paid_reply_texts_collects_all_sendable_fields():
    data = {
        "reply_options": [{"text": "الف"}, {"text": "ب"}, {"no_text": 1}],
        "copy_ready_reply": "ج",
        "safe_opening_line": "د",
    }
    assert set(_paid_reply_texts(data)) == {"الف", "ب", "ج", "د"}
