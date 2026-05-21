from app.schemas import FreeDecodeIn
from app.services.ai import classify


def _classify(message_text: str, relationship_type: str, user_goal: str):
    return classify(
        FreeDecodeIn(
            message_text=message_text,
            relationship_type=relationship_type,
            user_goal=user_goal,
            privacy_consent="none",
        )
    )


def test_generated_case_romantic_controlling_boundary():
    result = _classify(
        "حق نداری با اون آدم بری بیرون. من خوشم نمیاد ازش. اگه رفتی دیگه به من پیام نده.",
        "romantic",
        "set_boundary",
    )

    assert result.dominant_lens == "dopamine"
    assert "کنترل‌گر" in result.tones
    assert "تهدیدکننده" in result.tones


def test_generated_case_ex_sad_ambiguous_stays_oxytocin():
    result = _classify(
        "دیشب خوابتو دیدم. خیلی دلم گرفت. کاش می‌شد همه چی رو درست کرد...",
        "ex",
        "avoid_needy",
    )

    assert result.dominant_lens == "oxytocin"
    assert "غمگین" in result.tones
    assert "مبهم" in result.tones


def test_generated_case_customer_status_restoration():
    result = _classify(
        "شما اصلا می‌دونید من کی هستم که اینطوری با من حرف می‌زنید؟ مدیرتون رو صدا کنید!",
        "customer",
        "calm_conflict",
    )

    assert result.dominant_lens == "serotonin"
    assert "تند" in result.tones


def test_generated_case_unknown_protects_personal_info():
    result = _classify(
        "سلام یه پیشنهاد کاری فوق‌العاده با درآمد دلاری براتون دارم. شمارتون رو بذارید تماس بگیرم.",
        "unknown",
        "understand_only",
    )

    assert result.dominant_lens == "dopamine"
    assert "رسمی" in result.tones
