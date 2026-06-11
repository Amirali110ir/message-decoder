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
    golden_examples_as_messages,
    select_golden_examples,
)
from app.services.quality_rubric import copy_readiness, natural_persian


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


def test_golden_examples_cover_all_core_relationships():
    """P1 T7/T8: coverage extended beyond romantic to ex / work / family."""
    rels = {ex.relationship_type for ex in GOLDEN_EXAMPLES}
    assert {"romantic", "ex", "manager_colleague", "customer", "family"} <= rels
    # The highest-risk gap (ex) and the boundary/ending goals must be present.
    rom_goals = {ex.user_goal for ex in GOLDEN_EXAMPLES if ex.relationship_type == "romantic"}
    assert {"set_boundary", "end_conversation"} <= rom_goals
    assert any(ex.relationship_type == "ex" for ex in GOLDEN_EXAMPLES)


def test_golden_examples_have_no_defensive_or_jargon_text():
    for ex in GOLDEN_EXAMPLES:
        for bad in DEFENSIVE_EXCUSE_PHRASES + PSYCH_JARGON_PHRASES:
            assert bad not in ex.reply, f"{ex.id} contains forbidden phrase {bad}"


def test_golden_examples_pass_deterministic_quality_bar():
    """Every curated reply must itself clear the copy-readiness bar — a bad
    exemplar teaches the model bad style. This is the deterministic rubric gate
    that runs in CI without any API calls (P1 T13).

    natural_persian is a shekaste-calibrated scorer (it penalises formal markers
    like «بفرمایید»), so it only validly applies to personal-register replies;
    professional work/customer replies are gated on copy-readiness only.
    """
    for ex in GOLDEN_EXAMPLES:
        assert copy_readiness(ex.reply) >= 4, f"{ex.id} reply not copy-ready"
        if ex.relationship_type not in ("manager_colleague", "customer"):
            assert natural_persian(ex.reply) >= 3, f"{ex.id} reply reads unnatural"


def test_golden_selection_scopes_to_relationship_and_prefers_goal():
    sel = select_golden_examples("romantic", "avoid_needy", limit=4)
    assert sel and sel[0].user_goal == "avoid_needy"
    # Non-romantic relationships now have their own curated pools.
    mgr = select_golden_examples("manager_colleague", "set_boundary", limit=4)
    assert mgr and all(ex.relationship_type == "manager_colleague" for ex in mgr)
    assert mgr[0].user_goal == "set_boundary"
    # Unknown / uncovered relationships still fall back to the generic path.
    assert select_golden_examples("unknown", "calm_conflict") == []


def test_golden_examples_as_messages_are_alternating_turns():
    msgs = golden_examples_as_messages("ex", "set_boundary", limit=3)
    assert len(msgs) == 6  # 3 user/assistant pairs
    assert [m["role"] for m in msgs] == ["user", "assistant"] * 3


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
