"""Quality rubric runner (T2.2).

Scores the product's paid reply on a fixed set of wedge cases across 5 rubric
dimensions, so any prompt/model change can be measured before shipping.

  - copy_readiness, natural_persian        -> deterministic (app.services.quality_rubric)
  - emotional_accuracy, risk_reduction, boundary_quality -> LLM judge (1..5)

Run after each prompt/model change and compare the overall score to the
previous report. Output: docs/quality/rubric_report.md
"""

from __future__ import annotations

import asyncio
import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(".env")
import os  # noqa: E402

os.environ["AI_SEMANTIC_CACHE_ENABLED"] = "false"

from app.config import get_settings  # noqa: E402
from app.schemas import FreeDecodeIn  # noqa: E402
from app.services.ai import (  # noqa: E402
    PROMPT_VERSION,
    PaidDecodeUnavailable,
    current_model_version,
    free_decode,
    paid_decode,
)
from app.services.quality_rubric import deterministic_scores  # noqa: E402
from app.services.rule_engine import classify  # noqa: E402

OUT = Path(__file__).resolve().parents[3] / "docs" / "quality"
JUDGE_MODEL = "anthropic/claude-sonnet-4.5"

# Fixed rubric cases. Distinct from golden examples so few-shot can't copy them.
# Each case is (relationship_type, user_goal, incoming_message, optional_context).
# Keep existing cases STABLE (same position/text) so scores stay comparable across
# runs; only APPEND new cases. The first 10 are the original romantic wedge.
RUBRIC_CASES = [
    # --- romantic wedge (original 10, kept stable) ---
    ("romantic", "calm_conflict", "هر وقت حرف می‌زنم سرت تو گوشیته، انگار اصلا برات مهم نیست چی میگم.", None),
    ("romantic", "calm_conflict", "دیشب جلوی دوستات اونجوری جوابمو دادی، خیلی بهم برخورد.", None),
    ("romantic", "calm_conflict", "بازم قرارمونو کنسل کردی. دیگه نمی‌دونم باید چه حسی داشته باشم.", None),
    ("romantic", "calm_conflict", "حس می‌کنم هرچی می‌کشم به خاطر این رابطه‌ست و تو اصلا نمی‌بینی.", None),
    ("romantic", "avoid_needy", "(دو روزه جوابمو نداده و نمی‌خوام آویزون به نظر بیام)", None),
    ("romantic", "avoid_needy", "خب دیگه معلومه سرت شلوغه، مزاحمت نمیشم.", None),
    ("romantic", "calm_conflict", "انگار من همیشه آخرین اولویتتم، کار و رفیقات همیشه جلوترن.", None),
    ("romantic", "set_boundary", "چرا بدون اینکه به من بگی تصمیم گرفتی؟ من اصلا به حساب نمیام؟", None),
    ("romantic", "calm_conflict", "گفتی عوض میشی ولی هیچی فرق نکرده، دیگه امیدی ندارم.", None),
    ("romantic", "avoid_needy", "استوری گذاشتی ولی جواب منو ندادی. باشه، فهمیدم.", None),
    # --- ex (highest-risk gap) ---
    ("ex", "set_boundary", "میشه یه بار دیگه ببینمت؟ فقط یه قهوه، دلم برات تنگ شده.", None),
    ("ex", "end_conversation", "اصلا انگار نه انگار چند سال با هم بودیم. خیلی بی‌رحمی.", None),
    ("ex", "set_boundary", "بیداری؟ امشب خیلی حالم بده، فقط تو رو می‌خوام.", None),
    # --- manager / colleague (professional register) ---
    ("manager_colleague", "set_boundary", "این گزارشو باید همین امشب تا ساعت ۲ تمومش کنی و بفرستی.", None),
    ("manager_colleague", "calm_conflict", "تو جلسه گفتی کارو انجام دادی ولی من هیچ خروجی‌ای نمی‌بینم.", None),
    ("manager_colleague", "professional_reply", "این اصلا اون چیزی نبود که ازت خواسته بودم، دوباره انجامش بده.", None),
    # --- customer (brand voice) ---
    ("customer", "calm_conflict", "سفارشم یه هفته دیر شده، دیگه از خرید از شما پشیمونم.", None),
    ("customer", "set_boundary", "اگه همین الان پولمو برنگردونید، همه جا ازتون شکایت می‌کنم.", None),
    # --- family (soft but firm boundaries) ---
    ("family", "set_boundary", "کی می‌خوای ازدواج کنی؟ دیگه جلوی فامیل سرافکنده شدیم.", None),
    ("family", "calm_conflict", "دیگه اصلا بهمون سر نمی‌زنی، انگار واقعا برات غریبه شدیم.", None),
    # --- episode context (situation arc, not just last line) ---
    ("romantic", "calm_conflict", "هرچی می‌خوای فکر کن. من دیگه حرفی ندارم.",
     "دو هفته پیش سر مهمونی دعوامون شد و گفت دیگه بهم اعتماد نداره. از اون موقع سرد شده و کوتاه جواب می‌ده. دیروز گفتم بیا حرف بزنیم، اینو جواب داد."),
]

DIMENSIONS = ["natural_persian", "risk_reduction", "copy_readiness", "emotional_accuracy", "boundary_quality"]


async def _post(body: dict, retries: int = 2) -> str | None:
    s = get_settings()
    endpoint = s.ai_paid_api_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {s.ai_paid_api_key}", "Content-Type": "application/json"}
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=120) as c:
                r = await c.post(endpoint, headers=headers, json=body)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception:  # noqa: BLE001
            if attempt == retries:
                return None
            await asyncio.sleep(3)
    return None


LLM_DIMENSIONS = ["risk_reduction", "emotional_accuracy", "boundary_quality"]


async def judge_scores(message: str, reply: str, goal: str, relationship_type: str) -> dict[str, int] | None:
    """Return LLM-scored dimensions (1-5) or None if the judge call fails.

    Returning None (instead of zeros) ensures failed calls are excluded from
    averages rather than silently dragging scores down. The judge also receives
    user_goal and relationship_type so boundary_quality and risk_reduction are
    rated in context, not blindly.
    """
    prompt = (
        "تو یک ارزیابِ سخت‌گیرِ کیفیتِ پاسخ‌های فارسی در ارتباطاتِ بین‌فردی (عاطفی، کاری، خانوادگی، مشتری) هستی.\n"
        f"نوعِ رابطه: {relationship_type} | هدفِ کاربر: {goal}\n"
        f"پیامِ دریافتی: «{message}»\n"
        f"پاسخِ پیشنهادی به کاربر: «{reply}»\n\n"
        "این پاسخ را در سه بُعد از ۱ تا ۵ نمره بده:\n"
        "- risk_reduction: چقدر ریسکِ بدترشدنِ رابطه را کم می‌کند (دفاعی/تحریک‌کننده نبودن).\n"
        "- emotional_accuracy: چقدر احساسِ واقعیِ طرف را درست دیده و تأیید کرده (نه تأییدِ ادعا).\n"
        "- boundary_quality: چقدر مرزِ سالم نگه داشته بدون تحقیر یا التماس (با توجه به هدفِ کاربر).\n"
        'فقط JSON بده: {"risk_reduction":int,"emotional_accuracy":int,"boundary_quality":int}'
    )
    body = {
        "model": JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "max_tokens": 120,
        "response_format": {"type": "json_object"},
    }
    content = await _post(body)
    if not content:
        return None
    out: dict[str, int] = {}
    for k in LLM_DIMENSIONS:
        m = re.search(rf'"{k}"\s*:\s*([1-5])', content)
        if m:
            out[k] = int(m.group(1))
    # If fewer than all 3 dimensions parsed, treat it as a failed judge call.
    if len(out) < len(LLM_DIMENSIONS):
        return None
    return out


async def product_reply(
    relationship_type: str,
    goal: str,
    message: str,
    context: str | None = None,
    attempts: int = 3,
) -> str | None:
    """Generate the paid reply, retrying transient API timeouts."""
    payload = FreeDecodeIn(
        message_text=message,
        relationship_type=relationship_type,
        user_goal=goal,
        optional_context=context,
    )
    for attempt in range(attempts):
        try:
            fo = await free_decode(payload, classify(payload))
            po = await paid_decode(fo, relationship_type, goal, message_text=message, optional_context=context)
            return po.copy_ready_reply.strip()
        except PaidDecodeUnavailable:
            if attempt == attempts - 1:
                return None
            await asyncio.sleep(4)
    return None


async def main() -> None:
    rows = []
    for i, (relationship_type, goal, message, context) in enumerate(RUBRIC_CASES, 1):
        print(f"[{i}/{len(RUBRIC_CASES)}] scoring ({relationship_type}/{goal})...", flush=True)
        reply = await product_reply(relationship_type, goal, message, context)
        if reply is None:
            print(f"  ! skipped case {i} (paid unavailable after retries)", flush=True)
            continue
        det = deterministic_scores(reply)
        jud = await judge_scores(message, reply, goal=goal, relationship_type=relationship_type)
        if jud is None:
            print(f"  ! judge failed for case {i} — LLM dimensions excluded from averages", flush=True)
        scores = {**det, **(jud or {}), "judge_ok": jud is not None}
        rows.append({
            "i": i, "relationship_type": relationship_type, "goal": goal,
            "message": message, "reply": reply, "scores": scores,
        })

    if not rows:
        print("No cases scored (all paid calls failed). Aborting report.")
        return

    # Deterministic dimensions: average over all rows.
    # LLM dimensions: average only over rows where the judge succeeded.
    det_rows = rows
    llm_rows = [r for r in rows if r["scores"].get("judge_ok")]
    avg: dict[str, float] = {}
    for d in DIMENSIONS:
        if d in LLM_DIMENSIONS:
            avg[d] = round(sum(r["scores"].get(d, 0) for r in llm_rows) / len(llm_rows), 2) if llm_rows else 0.0
        else:
            avg[d] = round(sum(r["scores"].get(d, 0) for r in det_rows) / len(det_rows), 2)
    overall = round(sum(avg.values()) / len(DIMENSIONS), 2)

    OUT.mkdir(parents=True, exist_ok=True)
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    md = [
        "# گزارشِ rubric کیفیتِ پاسخِ پولی (T2.2)", "",
        f"- تاریخ: {ts}",
        f"- نسخه‌ی prompt: `{PROMPT_VERSION}` · مدلِ paid: `{current_model_version('paid')}`",
        f"- تعداد case: {len(rows)}  ·  قاضیِ بُعدهای ذهنی: `{JUDGE_MODEL}`", "",
        "## میانگینِ هر بُعد (۱ تا ۵)", "",
        "| بُعد | میانگین |", "| :-- | :--: |",
    ]
    for d in DIMENSIONS:
        md.append(f"| {d} | {avg[d]} |")
    md += [f"| **overall** | **{overall}** |", "",
           "> copy_readiness و natural_persian قطعی‌اند؛ بقیه با قاضیِ LLM.", "",
           "## جزئیاتِ هر case", "",
           "| # | رابطه | هدف | " + " | ".join(DIMENSIONS) + " | پاسخ |",
           "| :- | :- | :- |" + " :-: |" * len(DIMENSIONS) + " :-- |"]
    for r in rows:
        cells = " | ".join(str(r["scores"].get(d, 0)) for d in DIMENSIONS)
        reply_short = r["reply"].replace("\n", " ")
        md.append(f"| {r['i']} | {r.get('relationship_type', '')} | {r['goal']} | {cells} | {reply_short} |")
    (OUT / "rubric_report.md").write_text("\n".join(md), encoding="utf-8")
    (OUT / "rubric_latest.json").write_text(
        json.dumps({"ts": ts, "prompt_version": PROMPT_VERSION, "paid_model": current_model_version("paid"),
                    "averages": avg, "overall": overall, "rows": rows}, ensure_ascii=False, indent=2),
        encoding="utf-8",
    )
    print(f"\nOVERALL {overall}/5 | " + " ".join(f"{d}={avg[d]}" for d in DIMENSIONS))
    print(f"Report: {OUT / 'rubric_report.md'}")

    # Threshold gate (P1 T13): when run in CI, fail the job if quality regresses
    # below RUBRIC_MIN_OVERALL so a prompt/model change can't silently degrade
    # the paid reply. Defaults to 3.8/5; set to 0 to disable the gate.
    min_overall = float(os.getenv("RUBRIC_MIN_OVERALL", "3.8"))
    if min_overall > 0 and overall < min_overall:
        print(f"\n❌ QUALITY GATE FAILED: overall {overall} < threshold {min_overall}")
        sys.exit(1)
    print(f"\n✅ quality gate passed (overall {overall} ≥ {min_overall})")


if __name__ == "__main__":
    asyncio.run(main())
