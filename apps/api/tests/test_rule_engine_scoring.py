from app.schemas import FreeDecodeIn
from app.services.rule_engine import classify, paid_reply_playbook


def _payload(message_text: str, relationship_type: str = "unknown", user_goal: str = "understand_only") -> FreeDecodeIn:
    return FreeDecodeIn(
        message_text=message_text,
        relationship_type=relationship_type,
        user_goal=user_goal,
        privacy_consent="none",
    )


def test_controlling_tone_overrides_set_boundary_bias():
    result = classify(
        _payload(
            "حق نداری با اون آدم بری بیرون. اگه رفتی دیگه به من پیام نده.",
            relationship_type="romantic",
            user_goal="set_boundary",
        )
    )

    assert result.dominant_lens == "dopamine"
    assert result.lens_scores["dopamine"] > result.lens_scores["serotonin"]


def test_strong_status_signal_beats_professional_dopamine_bias():
    result = classify(
        _payload(
            "شما اصلا می‌دونید من کی هستم که اینطوری با من حرف می‌زنید؟",
            relationship_type="customer",
            user_goal="calm_conflict",
        )
    )

    assert result.dominant_lens == "serotonin"


def test_paid_playbook_uses_relationship_and_goal_catalogs():
    playbook = paid_reply_playbook("ex", "end_conversation", "oxytocin")

    assert "پایان‌دهنده" in playbook["must_include"]
    assert playbook["user_goal_playbook"]["priority"].startswith("خروج")
    assert "نوستالژی" in playbook["relationship_playbook"]["dont"]
