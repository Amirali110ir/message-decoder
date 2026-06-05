"""Re-run only the LLM judge over an existing answer_key.json and write the
three blind-test files to the CORRECT docs/blind_test path.

Avoids regenerating the (expensive) product/baseline replies. Fixes two bugs
from the first run: verbose judge reasons truncating the JSON, and the wrong
output directory.
"""

from __future__ import annotations

import asyncio
import json
import re
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(".env")

from app.config import get_settings  # noqa: E402

REPO = Path(__file__).resolve().parents[3]            # repo root (was parents[2] -> apps)
SRC = REPO / "apps" / "docs" / "blind_test" / "answer_key.json"  # where the first run wrote it
OUT = REPO / "docs" / "blind_test"
JUDGE_MODEL = "anthropic/claude-sonnet-4.5"


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
        except Exception as e:  # noqa: BLE001
            if attempt == retries:
                print(f"  ! judge failed: {type(e).__name__}", flush=True)
                return None
            await asyncio.sleep(3)
    return None


async def judge(message: str, a: str, b: str) -> tuple[str, str]:
    prompt = (
        "تو یک فارسی‌زبانِ معمولی هستی که می‌خوای به این پیام جواب بدی.\n"
        f"پیامِ دریافتی: «{message}»\n\n"
        f"جوابِ A: «{a}»\n"
        f"جوابِ B: «{b}»\n\n"
        "کدوم جواب رو راحت‌تر و با اطمینانِ بیشتر عیناً می‌فرستی؟ "
        "ملاک: آماده‌ی ارسال بودن، طبیعی و انسانی بودن، کم‌ریسک بودن. "
        'فقط JSON کوتاه بده: {"winner":"A" یا "B", "reason":"حداکثر ۸ کلمه"}'
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
        return "tie", "(judge unavailable)"
    # Lenient: pull the winner even if the JSON got truncated.
    m = re.search(r'"winner"\s*:\s*"?\s*([AB])', content)
    winner = m.group(1) if m else "tie"
    rm = re.search(r'"reason"\s*:\s*"([^"]{0,120})', content)
    reason = rm.group(1) if rm else ""
    return winner, reason


async def main() -> None:
    rows = json.loads(SRC.read_text(encoding="utf-8"))
    for r in rows:
        w, reason = await judge(r["message"], r["A"], r["B"])
        r["judge_winner"], r["judge_reason"] = w, reason
        print(f"[{r['i']:>2}] winner={w} (product={r['product_side']})", flush=True)

    OUT.mkdir(parents=True, exist_ok=True)
    (OUT / "answer_key.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # blind scoring sheet
    sheet = ["# تستِ کورِ فاز ۱ — کدام جواب را راحت‌تر می‌فرستی؟", "",
             "برای هر مورد فقط A یا B را علامت بزن. نمی‌دانی کدام محصول است.", ""]
    for r in rows:
        sheet += [f"## مورد {r['i']}", f"**پیام دریافتی:** {r['message']}", "",
                  f"- **A:** {r['A']}", f"- **B:** {r['B']}", "", "انتخاب: ☐ A ☐ B", "", "---", ""]
    (OUT / "scoring_sheet.md").write_text("\n".join(sheet), encoding="utf-8")

    prod = sum(1 for r in rows if r["judge_winner"] == r["product_side"])
    base = sum(1 for r in rows if r["judge_winner"] in ("A", "B") and r["judge_winner"] != r["product_side"])
    ties = len(rows) - prod - base
    decided = prod + base
    rate = (prod / decided) if decided else 0.0
    jr = [f"# قاضیِ خودکار (مدل: {JUDGE_MODEL}) — سیگنالِ مقدماتی", "",
          f"- محصول برد: **{prod}** / ChatGPT خام برد: **{base}** / مساوی: **{ties}**",
          f"- نرخِ برتریِ محصول (بینِ موارد قطعی): **{rate*100:.0f}%**  (شرطِ دروازه: ۷۰٪)",
          f"- حکم: {'✅ عبور (سیگنال ماشینی)' if rate >= 0.7 else '❌ هنوز نه (سیگنال ماشینی)'}", "",
          "> سیگنالِ یک قاضیِ ماشینی است؛ دروازه‌ی واقعی قضاوتِ ۱۰ فارسی‌زبان است.", "",
          "| # | هدف | برنده | محصول کدام بود | دلیلِ قاضی |", "| :- | :- | :- | :- | :- |"]
    for r in rows:
        jr.append(f"| {r['i']} | {r['goal']} | {r['judge_winner']} | {r['product_side']} | {r['judge_reason']} |")
    (OUT / "llm_judge_results.md").write_text("\n".join(jr), encoding="utf-8")

    print(f"\nproduct {prod} / baseline {base} / tie {ties} -> preference {rate*100:.0f}%")
    print(f"Files in {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
