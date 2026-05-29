import pytest
from app.schemas import FreeDecodeIn
from app.services.ai import classify, free_decode, paid_decode
from app.services.contact_memory import summarize_message_focus
from app.utils import normalize_persian


def test_rule_engine_detects_tone_need_and_strategy():
    payload = FreeDecodeIn(
        message_text="باشه، هر جور راحتی. معلومه من اصلا برات مهم نیستم.",
        relationship_type="romantic",
        user_goal="avoid_needy",
        privacy_consent="none",
    )

    classification = classify(payload)

    assert classification.dominant_lens == "oxytocin"
    assert "سرد" in classification.tones
    assert "کنایه‌آمیز" in classification.tones
    assert "validate_feeling" in classification.reply_strategy
    assert classification.words_to_avoid


@pytest.mark.anyio
async def test_fallback_paid_decode_generates_more_varied_replies():
    payload = FreeDecodeIn(
        message_text="باشه، هر جور راحتی. معلومه من اصلا برات مهم نیستم.",
        relationship_type="romantic",
        user_goal="avoid_needy",
        privacy_consent="none",
    )
    free = await free_decode(payload, classify(payload))
    paid = await paid_decode(free, "romantic", "avoid_needy")

    labels = {reply.label for reply in paid.reply_options}
    assert {"نرم", "تعیین‌کننده مرز روابط", "کوتاه", "قاطع و آرام"}.issubset(labels)
    assert paid.words_to_avoid


def test_persian_normalization():
    # Test Arabic Kaf and Yeh mapping
    arabic_text = "كتاب علي در اتاق است."
    normalized = normalize_persian(arabic_text)
    assert "کتاب" in normalized
    assert "علی" in normalized
    assert "ك" not in normalized
    assert "ي" not in normalized

    # Test Arabic Teh Marbuta and Alef variations
    arabic_text_2 = "إستفاده از گزینة مناسب"
    normalized_2 = normalize_persian(arabic_text_2)
    assert "استفاده" in normalized_2
    assert "گزینه" in normalized_2

    # Test ZWNJ standardization
    zwnj_text = "می\u200cخواهم بروم"
    normalized_3 = normalize_persian(zwnj_text)
    assert "می‌خواهم" in normalized_3

    # Test text containing Arabic/Persian letters under classify
    payload = FreeDecodeIn(
        message_text="من اصلا برات مهم نيستم كاش بگی.",  # Contains Arabic Y and K
        relationship_type="romantic",
        user_goal="avoid_needy",
        privacy_consent="none",
    )
    classification = classify(payload)
    # The normalizer will clean it up, and the rule engine will work correctly
    assert classification.dominant_lens == "oxytocin"


def test_safety_precision():
    # Casual messages should NOT trigger high-risk safety
    casual_payload_1 = FreeDecodeIn(
        message_text="سلام، لوکیشنتو بفرست تا ببینم کجایی.",
        relationship_type="romantic",
        user_goal="avoid_needy",
        privacy_consent="none",
    )
    classification_1 = classify(casual_payload_1)
    assert classification_1.safety_label != "high_risk"

    casual_payload_2 = FreeDecodeIn(
        message_text="من منتظرم دم در خونت، بیا بیرون.",
        relationship_type="romantic",
        user_goal="avoid_needy",
        privacy_consent="none",
    )
    classification_2 = classify(casual_payload_2)
    assert classification_2.safety_label != "high_risk"

    # Serious threats should trigger high-risk safety
    threat_payload_1 = FreeDecodeIn(
        message_text="اگه ازم جدا بشی می‌کشمت پشیمون میشی.",
        relationship_type="romantic",
        user_goal="avoid_needy",
        privacy_consent="none",
    )
    classification_3 = classify(threat_payload_1)
    assert classification_3.safety_label == "high_risk"
    assert "violence" in classification_3.safety_reasons

    threat_payload_2 = FreeDecodeIn(
        message_text="همه عکساتو پخش میکنم و آبروتو میبرم اگه پول ندی.",
        relationship_type="romantic",
        user_goal="avoid_needy",
        privacy_consent="none",
    )
    classification_4 = classify(threat_payload_2)
    assert classification_4.safety_label == "high_risk"
    assert "blackmail" in classification_4.safety_reasons


@pytest.mark.anyio
async def test_dynamic_fallback_playbooks():
    payload = FreeDecodeIn(
        message_text="کارها چطور پیش میره؟",
        relationship_type="manager_colleague",
        user_goal="professional_reply",
        privacy_consent="none",
    )
    free = await free_decode(payload, classify(payload))

    # Test Professional relationship category fallback
    paid_prof = await paid_decode(free, "manager_colleague", "professional_reply")
    prof_labels = {reply.label for reply in paid_prof.reply_options}
    assert "حرفه‌ای" in prof_labels
    assert "کوتاه" in prof_labels
    assert "تعیین‌کننده مرز روابط" in prof_labels
    assert "قاطع و آرام" in prof_labels
    assert "سرم شلوغ بود" in paid_prof.words_to_avoid

    # Test Ex relationship category fallback
    paid_ex = await paid_decode(free, "ex", "end_conversation")
    ex_labels = {reply.label for reply in paid_ex.reply_options}
    assert "پایان‌دهنده" in ex_labels
    assert "تعیین‌کننده مرز روابط" in ex_labels
    assert "دلم برات تنگ شده" in paid_ex.words_to_avoid


@pytest.mark.anyio
async def test_message_focus_anchors_generic_fallback_replies():
    payload = FreeDecodeIn(
        message_text="من اشتباه کردم داروخانه زدم",
        relationship_type="unknown",
        user_goal="understand_only",
        privacy_consent="none",
    )
    focus = summarize_message_focus(payload)
    free = await free_decode(payload, classify(payload), message_focus=focus)
    paid = await paid_decode(free, "unknown", "understand_only")

    assert "داروخانه" in free.message_focus
    assert "داروخانه" in free.why_this_lens
    assert "داروخانه" in paid.copy_ready_reply
