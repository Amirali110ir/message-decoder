"""Tests for the deterministic rubric scorers (T2.2)."""

from app.services.quality_rubric import copy_readiness, natural_persian, deterministic_scores


def test_copy_readiness_high_for_clean_short_reply():
    text = "می‌فهمم چرا دلخوری. تو برام مهمی. بیا حرف بزنیم."
    assert copy_readiness(text) >= 4


def test_copy_readiness_penalises_meta_option_framing():
    text = "بسته به اینکه چقدر می‌خواهید صمیمانه باشید، یکی از گزینه‌های زیر را انتخاب کنید."
    assert copy_readiness(text) <= 2


def test_copy_readiness_penalises_defensive_excuse():
    text = "ببخشید، راستش سرم شلوغ بود و نتونستم جواب بدم."
    assert copy_readiness(text) <= 3


def test_natural_persian_high_for_shekaste():
    text = "می‌دونم ناراحتی، نمی‌خوام اینجوری باشه. بهت میگم چی شد."
    assert natural_persian(text) >= 4


def test_natural_persian_low_for_formal_robotic():
    text = "خواهشمند است در اسرع وقت پاسخ بفرمایید تا اقدام مقتضی صورت گیرد."
    assert natural_persian(text) <= 2


def test_deterministic_scores_shape():
    s = deterministic_scores("سلام، چطوری؟")
    assert set(s.keys()) == {"copy_readiness", "natural_persian"}
    assert all(1 <= v <= 5 for v in s.values())
