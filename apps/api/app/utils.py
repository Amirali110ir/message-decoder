from __future__ import annotations

import json
import re
import secrets
from datetime import datetime, timezone
from typing import Any


def now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def new_id(prefix: str) -> str:
    return f"{prefix}_{secrets.token_hex(8)}"


def dumps(data: Any) -> str:
    return json.dumps(data, ensure_ascii=False)


def loads(value: str | None, default: Any = None) -> Any:
    if not value:
        return default
    return json.loads(value)


def anonymize_text(text: str) -> str:
    text = re.sub(r"\b09\d{9}\b", "[شماره موبایل]", text)
    text = re.sub(r"\b\d{8,}\b", "[عدد حساس]", text)
    text = re.sub(r"[\w.\-+]+@[\w.\-]+\.[A-Za-z]{2,}", "[ایمیل]", text)
    return text.strip()


def has_sensitive_info(text: str) -> bool:
    return bool(
        re.search(r"\b09\d{9}\b", text)
        or re.search(r"[\w.\-+]+@[\w.\-]+\.[A-Za-z]{2,}", text)
        or re.search(r"\b\d{8,}\b", text)
    )


def normalize_persian(text: str) -> str:
    if not text:
        return ""
    # Map Arabic Kaf/Yeh variations to standard Persian
    arabic_to_persian = {
        "ي": "ی",
        "ى": "ی",
        "ك": "ک",
        "ة": "ه",
        "أ": "ا",
        "إ": "ا",
        "آ": "ا",
    }
    for arabic_char, persian_char in arabic_to_persian.items():
        text = text.replace(arabic_char, persian_char)
    
    # Standardize zero-width non-joiner (ZWNJ / نیم‌فاصله)
    # Convert various ZWNJ encodings or common spaces between prefix/suffix
    text = text.replace("\u200c", "‌")  # Standardize ZWNJ character
    
    # Remove excessive whitespace
    text = re.sub(r"\s+", " ", text)
    return text.strip()


