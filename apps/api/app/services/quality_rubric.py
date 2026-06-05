"""Quality rubric for paid replies (T2.2).

Two deterministic, unit-testable dimensions live here:
  - copy_readiness  : is it actually sendable as-is? (length, sentence count,
                      no meta "choose an option" framing, no forbidden phrases)
  - natural_persian : does it read like a real person texting? (shekaste /
                      colloquial markers vs formal/robotic endings, no jargon)

The subjective dimensions (emotional_accuracy, risk_reduction, boundary_quality)
are scored by an LLM judge in scripts/quality_rubric.py — they need semantic
judgement that a heuristic cannot give.

All scores are on a 1..5 scale.
"""

from __future__ import annotations

import re

from app.services.ai import DEFENSIVE_EXCUSE_PHRASES, PSYCH_JARGON_PHRASES

# Meta framing that betrays a "ChatGPT gives you options" answer rather than a
# ready-to-send reply.
_META_FRAMING = ["گزینه", "بسته به", "می‌توانید یکی", "می توانید یکی", "پیشنهاد می‌کنم یکی", "حالت زیر", "مورد زیر"]

# Colloquial (shekaste) markers — how Iranians actually text.
_SHEKASTE_MARKERS = ["می‌خوام", "نمی‌خوام", "بهت", "ازت", "نمی‌دونم", "می‌دونم", "میشه", "نمیشه",
                     "باهات", "دلخوری", "بریم", "بگو", "حواسم", "برام", "اینجوری", "اینطوری", "چیه"]

# Formal / robotic markers that should NOT appear in a chat reply.
_FORMAL_MARKERS = ["می‌باشد", "می باشد", "می‌نمایم", "می‌گردد", "گردید", "بفرمایید", "اینجانب",
                   "خواهشمند", "مقتضی", "نمایید", "می‌نمایید"]


def _sentence_count(text: str) -> int:
    parts = [p for p in re.split(r"[.؟!\n]+", text) if p.strip()]
    return len(parts)


def copy_readiness(text: str) -> int:
    """1..5 — can the user paste-and-send this as-is?"""
    t = (text or "").strip()
    if not t:
        return 1
    score = 5
    # Meta "here are options" framing is the biggest copy-readiness killer.
    if any(m in t for m in _META_FRAMING):
        score -= 3
    # Forbidden defensive excuses / jargon make it unsendable.
    if any(p in t for p in (*DEFENSIVE_EXCUSE_PHRASES, *PSYCH_JARGON_PHRASES)):
        score -= 2
    # Too long for a chat message.
    if _sentence_count(t) > 4 or len(t) > 320:
        score -= 1
    return max(1, min(5, score))


def natural_persian(text: str) -> int:
    """1..5 — does it read like a real person texting (shekaste), not a bot?"""
    t = (text or "").strip()
    if not t:
        return 1
    score = 3
    if any(m in t for m in _SHEKASTE_MARKERS):
        score += 2
    if any(m in t for m in _FORMAL_MARKERS):
        score -= 2
    if any(p in t for p in PSYCH_JARGON_PHRASES):
        score -= 1
    return max(1, min(5, score))


def deterministic_scores(text: str) -> dict[str, int]:
    return {
        "copy_readiness": copy_readiness(text),
        "natural_persian": natural_persian(text),
    }
