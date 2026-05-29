from __future__ import annotations

import json
import re
import sqlite3
from dataclasses import dataclass
from typing import Any

from app.schemas import FreeDecodeIn, FreeDecodeOutput
from app.services.rule_engine import Classification
from app.utils import new_id, now_iso, normalize_persian


LENS_FA = {
    "dopamine": "هدف و کنترل",
    "oxytocin": "امنیت و اعتماد",
    "serotonin": "شأن و احترام",
}


@dataclass
class ContactMemory:
    id: str
    name: str
    relationship_type: str
    default_goal: str | None
    profile_summary: str | None
    memory_summary: str | None
    memory_json: dict[str, Any]


def resolve_contact_for_decode(
    conn: sqlite3.Connection,
    *,
    user_id: str | None,
    payload: FreeDecodeIn,
) -> ContactMemory | None:
    if not user_id or payload.ghost_mode:
        return None

    if payload.contact_id:
        row = conn.execute(
            "SELECT * FROM contacts WHERE id = ? AND user_id = ?",
            (payload.contact_id, user_id),
        ).fetchone()
        return _contact_from_row(row) if row else None

    name = extract_contact_name(payload)
    if not name:
        return None

    existing = conn.execute(
        "SELECT * FROM contacts WHERE user_id = ? AND lower(name) = lower(?)",
        (user_id, name),
    ).fetchone()
    if existing:
        return _contact_from_row(existing)

    contact_id = new_id("ct")
    created_at = now_iso()
    conn.execute(
        """
        INSERT INTO contacts (
            id, user_id, name, relationship_type, default_goal, profile_summary,
            interaction_count, created_at, updated_at
        ) VALUES (?, ?, ?, ?, ?, ?, 0, ?, ?)
        """,
        (
            contact_id,
            user_id,
            name,
            payload.relationship_type,
            payload.user_goal,
            f"پرونده اولیه از متن/زمینه ساخته شد: {name}.",
            created_at,
            created_at,
        ),
    )
    row = conn.execute("SELECT * FROM contacts WHERE id = ?", (contact_id,)).fetchone()
    return _contact_from_row(row) if row else None


def extract_contact_name(payload: FreeDecodeIn) -> str | None:
    if payload.contact_name and payload.contact_name.strip():
        return _clean_contact_name(payload.contact_name)

    text = normalize_persian("\n".join(part for part in (payload.optional_context, payload.message_text) if part))
    patterns = [
        r"(?:^|[\s،.])(?P<name>[\u0600-\u06FFA-Za-z][\u0600-\u06FFA-Za-z\s‌]{1,28}?)\s+(?:این\s+)?پیام(?:و| را)?\s+(?:فرستاده|فرستاد|داده|داد)",
        r"(?:پیام|متن)\s+(?:از|مال)\s+(?P<name>[\u0600-\u06FFA-Za-z][\u0600-\u06FFA-Za-z\s‌]{1,28})",
        r"(?:^|[\s،.])(?P<name>[\u0600-\u06FFA-Za-z][\u0600-\u06FFA-Za-z\s‌]{1,28}?)\s+(?:گفته|گفت|نوشته|نوشت)\s*[:：]",
        r"(?:^|[\s،.])(?P<name>[\u0600-\u06FFA-Za-z][\u0600-\u06FFA-Za-z\s‌]{1,28}?)\s+به(?:م| من)\s+(?:گفته|گفت)",
    ]
    for pattern in patterns:
        match = re.search(pattern, text)
        if match:
            cleaned = _clean_contact_name(match.group("name"))
            if cleaned:
                return cleaned
    return None


def summarize_message_focus(payload: FreeDecodeIn, contact: ContactMemory | None = None) -> str:
    text = normalize_persian("\n".join(part for part in (payload.optional_context, payload.message_text) if part)).strip()
    compact = re.sub(r"\s+", " ", text)
    message_only = normalize_persian(payload.message_text).strip()
    context_only = normalize_persian(payload.optional_context or "").strip()

    topic = _known_topic(compact)
    regret = any(term in compact for term in ("اشتباه کردم", "پشیمونم", "پشیمانم", "ای کاش", "کاش نمی"))
    decision = any(term in compact for term in ("تصمیم", "زدم", "راه انداختم", "شروع کردم", "قبول کردم"))

    if topic and regret:
        return f"پشیمانی یا تردید درباره {topic}"
    if topic and decision:
        return f"تصمیم یا اقدام مربوط به {topic}"
    if topic:
        return f"موضوع {topic}"

    about_match = re.search(r"(?:در مورد|درباره|راجع به|سر موضوع|موضوع)\s+([^،.؟!\n]{2,60})", compact)
    if about_match:
        return about_match.group(1).strip()

    if contact:
        return f"پیام/زمینه اخیر در رابطه با {contact.name}"

    if any(term in message_only for term in ("برات مهم نیست", "مهم نیستم", "اهمیت ندارم")):
        return "دلخوری از بی‌اهمیت دیده شدن"
    if any(term in message_only for term in ("هر جور راحتی", "باشه هر جور", "دیگه مهم نیست")):
        return "پیام سرد یا کنایه‌آمیز بعد از دلخوری"
    if any(term in message_only for term in ("چرا هنوز", "قرار بود", "پیگیری کنم")):
        return "پیگیری و فشار برای نتیجه مشخص"
    if context_only:
        return context_only[:70]
    return "موضوع همین پیام"


def build_contact_prompt_context(contact: ContactMemory | None, message_focus: str) -> str | None:
    if not contact:
        return None

    parts = [
        f"پرونده مخاطب: {contact.name}",
        f"نوع رابطه ثبت‌شده: {contact.relationship_type}",
    ]
    if contact.default_goal:
        parts.append(f"هدف پیش‌فرض کاربر با این مخاطب: {contact.default_goal}")
    if contact.profile_summary:
        parts.append(f"خلاصه دستی/قبلی: {contact.profile_summary}")
    if contact.memory_summary:
        parts.append(f"حافظه رفتاری استخراج‌شده: {contact.memory_summary}")

    lens_counts = contact.memory_json.get("lens_counts") or {}
    if lens_counts:
        dominant = max(lens_counts, key=lens_counts.get)
        parts.append(f"لنز پرتکرار در پیام‌های قبلی این مخاطب: {LENS_FA.get(dominant, dominant)}")

    recent_contexts = contact.memory_json.get("recent_contexts") or []
    if recent_contexts:
        parts.append(f"زمینه‌های اخیر: {'؛ '.join(recent_contexts[-3:])}")

    parts.append(f"موضوع فعلی که باید در تحلیل و پاسخ دیده شود: {message_focus}")
    return "\n".join(parts)


def update_contact_memory(
    conn: sqlite3.Connection,
    *,
    contact_id: str | None,
    user_id: str | None,
    payload: FreeDecodeIn,
    classification: Classification,
    free_output: FreeDecodeOutput,
    message_focus: str,
) -> str | None:
    if not contact_id or not user_id or payload.ghost_mode:
        return None

    row = conn.execute(
        "SELECT * FROM contacts WHERE id = ? AND user_id = ?",
        (contact_id, user_id),
    ).fetchone()
    if not row:
        return None

    memory = _load_memory(row["memory_json"])
    memory.setdefault("version", 1)
    lens_counts = memory.setdefault("lens_counts", {})
    tone_counts = memory.setdefault("tone_counts", {})
    recent_contexts = memory.setdefault("recent_contexts", [])
    guidance = memory.setdefault("reply_guidance", [])

    lens_counts[classification.dominant_lens] = int(lens_counts.get(classification.dominant_lens, 0)) + 1
    for tone in classification.tones:
        tone_counts[tone] = int(tone_counts.get(tone, 0)) + 1

    if message_focus and message_focus not in recent_contexts:
        recent_contexts.append(message_focus)
    del recent_contexts[:-5]

    if free_output.recommended_direction and free_output.recommended_direction not in guidance:
        guidance.append(free_output.recommended_direction)
    del guidance[:-4]

    memory["last_focus"] = message_focus
    memory["last_need"] = free_output.likely_underlying_need
    memory["last_risk"] = free_output.conversation_risk
    memory["updated_at"] = now_iso()

    memory_summary = build_memory_summary(
        contact_name=str(row["name"]),
        relationship_type=str(row["relationship_type"]),
        memory=memory,
    )
    profile_summary = _merge_profile_summary(row["profile_summary"], memory_summary)
    conn.execute(
        """
        UPDATE contacts
        SET profile_summary = ?, memory_summary = ?, memory_json = ?, updated_at = ?
        WHERE id = ? AND user_id = ?
        """,
        (
            profile_summary,
            memory_summary,
            json.dumps(memory, ensure_ascii=False),
            now_iso(),
            contact_id,
            user_id,
        ),
    )
    return memory_summary


def build_memory_summary(*, contact_name: str, relationship_type: str, memory: dict[str, Any]) -> str:
    lens_counts = memory.get("lens_counts") or {}
    tone_counts = memory.get("tone_counts") or {}
    contexts = memory.get("recent_contexts") or []
    guidance = memory.get("reply_guidance") or []

    if lens_counts:
        dominant_lens = max(lens_counts, key=lens_counts.get)
        lens_text = LENS_FA.get(dominant_lens, dominant_lens)
    else:
        lens_text = "نامشخص"

    top_tones = sorted(tone_counts, key=tone_counts.get, reverse=True)[:2]
    tone_text = "، ".join(top_tones) if top_tones else "هنوز الگوی لحن کافی ندارد"
    context_text = "؛ ".join(contexts[-3:]) if contexts else "زمینه تکرارشونده کافی ثبت نشده"
    guidance_text = guidance[-1] if guidance else "پاسخ‌ها باید کوتاه، مشخص و بدون ذهن‌خوانی قطعی باشند."

    return (
        f"{contact_name} در رابطه {relationship_type} تا اینجا بیشتر از لنز «{lens_text}» دیده شده؛ "
        f"لحن‌های پرتکرار: {tone_text}. زمینه‌های اخیر: {context_text}. "
        f"راهنمای پاسخ بعدی: {guidance_text}"
    )[:1200]


def _contact_from_row(row: sqlite3.Row | None) -> ContactMemory | None:
    if not row:
        return None
    return ContactMemory(
        id=str(row["id"]),
        name=str(row["name"]),
        relationship_type=str(row["relationship_type"]),
        default_goal=row["default_goal"],
        profile_summary=row["profile_summary"],
        memory_summary=row["memory_summary"] if "memory_summary" in row.keys() else None,
        memory_json=_load_memory(row["memory_json"] if "memory_json" in row.keys() else None),
    )


def _load_memory(raw: str | None) -> dict[str, Any]:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
        return value if isinstance(value, dict) else {}
    except json.JSONDecodeError:
        return {}


def _known_topic(text: str) -> str | None:
    topics = [
        ("داروخانه", "تصمیم راه‌اندازی داروخانه"),
        ("مهاجرت", "مهاجرت"),
        ("طلاق", "طلاق یا جدایی"),
        ("ازدواج", "ازدواج"),
        ("کار", "کار"),
        ("پول", "پول"),
        ("قرارداد", "قرارداد"),
        ("خانه", "خانه"),
        ("خونه", "خانه"),
        ("سرمایه", "سرمایه‌گذاری"),
        ("وام", "وام"),
        ("دانشگاه", "دانشگاه"),
    ]
    for needle, label in topics:
        if needle in text:
            return label
    return None


def _clean_contact_name(value: str | None) -> str | None:
    if not value:
        return None
    cleaned = normalize_persian(value)
    cleaned = re.sub(r"[\n\r:：،,.؟!]+", " ", cleaned)
    cleaned = re.sub(r"\s+", " ", cleaned).strip()
    cleaned = re.sub(r"^(مثلا|مثلاً|که|وقتی|بعد از اینکه|از طرف)\s+", "", cleaned).strip()
    words = cleaned.split()
    if not words or len(words) > 3:
        return None
    if cleaned in {"من", "تو", "کاربر", "طرف مقابل", "این پیام"}:
        return None
    return cleaned[:100]


def _merge_profile_summary(existing: str | None, memory_summary: str) -> str:
    base = (existing or "").strip()
    if not base:
        return memory_summary[:2000]
    marker = "حافظه سیستم:"
    manual = base.split(marker, 1)[0].strip()
    merged = f"{manual} {marker} {memory_summary}".strip()
    return merged[:2000]
