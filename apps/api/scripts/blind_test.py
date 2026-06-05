"""Phase-1 blind test harness: product pipeline vs raw-ChatGPT baseline.

For each of 20 realistic romantic messages we generate:
  A) the product reply  -> full pipeline (rule engine + v0.4 prompt + few-shot
     + post-gen inspector + self-critique), i.e. paid_decode().copy_ready_reply
  B) a raw baseline     -> a single plain call to the SAME paid model with a
     generic "you are a helpful Persian assistant, write a reply" prompt and
     none of our prompt engineering. This simulates pasting into ChatGPT.

Outputs (under docs/blind_test/):
  - scoring_sheet.md      : blind, randomised A/B, for the 10 human judges
  - answer_key.json       : per-item mapping of which side is the product
  - llm_judge_results.md   : preliminary automated judge tally toward the 70% gate

The human panel is the real gate; the LLM judge is only a directional signal.
"""

from __future__ import annotations

import asyncio
import json
import os
import random
from pathlib import Path

import httpx
from dotenv import load_dotenv

load_dotenv(".env")
os.environ["AI_SEMANTIC_CACHE_ENABLED"] = "false"  # always fresh for the test

from app.config import get_settings  # noqa: E402
from app.schemas import FreeDecodeIn  # noqa: E402
from app.services.ai import _model_for_task, free_decode, paid_decode  # noqa: E402
from app.services.rule_engine import classify  # noqa: E402

OUT = Path(__file__).resolve().parents[3] / "docs" / "blind_test"  # repo root
JUDGE_MODEL = "anthropic/claude-sonnet-4.5"  # strong, neutral, good at Persian

# 20 realistic romantic messages — deliberately DIFFERENT from the golden
# examples so few-shot can't copy them verbatim. (relationship=romantic.)
TEST_CASES = [
    ("calm_conflict", "هر وقت من حرف می‌زنم تو سرت تو گوشیته. انگار اصلا حضور ندارم برات."),
    ("calm_conflict", "دیشب جلوی دوستات اونجوری باهام حرف زدی، خیلی بد شد حالم."),
    ("calm_conflict", "تو همیشه طرف خانوادتو می‌گیری، انگار من هیچی‌ام."),
    ("calm_conflict", "چند روزه حس می‌کنم یه چیزی فرق کرده. دیگه مثل قبل نیستی."),
    ("calm_conflict", "بازم قرارمونو کنسل کردی. دیگه روم نمیشه به بقیه بگم برنامه دارم باهات."),
    ("calm_conflict", "من که هرچی میگم اشتباهه. بهتره دیگه اصلا حرف نزنم."),
    ("calm_conflict", "چرا همیشه باید من باشم که عذرخواهی می‌کنم؟"),
    ("calm_conflict", "تو رو خدا انقدر بهم نگو آروم باش. همینش عصبیم می‌کنه."),
    ("calm_conflict", "حس می‌کنم فقط وقتی بهت نیاز دارم نیستی."),
    ("calm_conflict", "اون پیامتو دیدم به دوستت. چرا درباره من اونجوری گفتی؟"),
    ("avoid_needy", "(دو روزه جوابِ پیامم رو نداده و من نمی‌خوام آویزون به نظر بیام)"),
    ("avoid_needy", "خب دیگه، انگار سرت شلوغه. مزاحمت نمیشم."),
    ("avoid_needy", "ولش کن، اصلا مهم نبود. خودت می‌دونی."),
    ("avoid_needy", "(می‌خوام بعد از یه هفته بی‌خبری بهش پیام بدم ولی نمی‌خوام دلخوری نشون بدم)"),
    ("avoid_needy", "نمی‌دونم چرا دارم اینو می‌گم، ولی دلم برات تنگ شده."),
    ("set_boundary", "چرا بدون اینکه به من بگی رفتی؟ باید همه چیزو از بقیه بشنوم؟"),
    ("calm_conflict", "انگار من برات در اولویت آخرم. کار و رفیقات همیشه جلوترن."),
    ("calm_conflict", "تو که گفتی عوض میشی. ولی هیچی فرق نکرده."),
    ("calm_conflict", "نمی‌خواد به خاطر من کاری کنی. خودم تنهایی عادت کردم."),
    ("avoid_needy", "دیدم استوری گذاشتی ولی جواب منو ندادی. باشه فهمیدم دیگه."),
]


async def _post_chat(body: dict, retries: int = 2) -> str | None:
    """POST to the chat endpoint with retries; returns content or None on failure."""
    settings = get_settings()
    endpoint = settings.ai_paid_api_base_url.rstrip("/") + "/chat/completions"
    headers = {"Authorization": f"Bearer {settings.ai_paid_api_key}", "Content-Type": "application/json"}
    for attempt in range(retries + 1):
        try:
            async with httpx.AsyncClient(timeout=120) as client:
                r = await client.post(endpoint, headers=headers, json=body)
                r.raise_for_status()
                return r.json()["choices"][0]["message"]["content"].strip()
        except Exception as e:  # noqa: BLE001 — best-effort harness
            if attempt == retries:
                print(f"   ! call failed after {retries+1} tries: {type(e).__name__}", flush=True)
                return None
            await asyncio.sleep(3)
    return None


async def product_reply(goal: str, message: str) -> str:
    try:
        payload = FreeDecodeIn(message_text=message, relationship_type="romantic", user_goal=goal)
        classification = classify(payload)
        fo = await free_decode(payload, classification)
        po = await paid_decode(fo, "romantic", goal, message_text=message)
        return po.copy_ready_reply.strip()
    except Exception as e:  # noqa: BLE001
        print(f"   ! product failed: {type(e).__name__}", flush=True)
        return "(محصول: تولید نشد)"


async def baseline_reply(message: str) -> str:
    """Raw single-call baseline — no NeuroLens prompt, no few-shot, no critique."""
    body = {
        "model": _model_for_task("paid"),
        "messages": [
            {"role": "system", "content": "تو یک دستیار فارسی‌زبان هستی. به کاربر کمک کن به پیامی که دریافت کرده یک جواب خوب بنویسد. فقط متنِ جوابِ پیشنهادی را بده."},
            {"role": "user", "content": f"این پیام بهم اومده، چه جوابی بدم؟\n«{message}»"},
        ],
        "temperature": 0.7,
    }
    return (await _post_chat(body)) or "(خام: تولید نشد)"


async def llm_judge(message: str, a: str, b: str) -> tuple[str, str]:
    """Return (winner 'A'|'B'|'tie', one-line reason). Blind to which is product."""
    prompt = (
        "تو یک فارسی‌زبانِ معمولی هستی که می‌خوای به این پیام جواب بدی.\n"
        f"پیامِ دریافتی: «{message}»\n\n"
        f"جوابِ A: «{a}»\n"
        f"جوابِ B: «{b}»\n\n"
        "کدوم جواب رو راحت‌تر و با اطمینانِ بیشتر می‌فرستی؟ "
        "فقط یک JSON بده: {\"winner\": \"A\" یا \"B\" یا \"tie\", \"reason\": \"یک جمله\"}"
    )
    body = {
        "model": JUDGE_MODEL,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": 0.2,
        "response_format": {"type": "json_object"},
    }
    content = await _post_chat(body)
    if content is None:
        return "tie", "(judge unavailable)"
    try:
        data = json.loads(content)
        winner = str(data.get("winner", "tie")).strip().upper()
        winner = winner if winner in ("A", "B") else "tie"
        return winner, str(data.get("reason", ""))
    except Exception:
        return "tie", "(parse error)"


async def main() -> None:
    OUT.mkdir(parents=True, exist_ok=True)
    rng = random.Random(42)
    rows = []
    for i, (goal, message) in enumerate(TEST_CASES, 1):
        print(f"[{i}/{len(TEST_CASES)}] generating...", flush=True)
        prod, base = await asyncio.gather(product_reply(goal, message), baseline_reply(message))
        product_is_a = rng.random() < 0.5
        a, b = (prod, base) if product_is_a else (base, prod)
        winner, reason = await llm_judge(message, a, b)
        rows.append({
            "i": i, "goal": goal, "message": message,
            "A": a, "B": b,
            "product_side": "A" if product_is_a else "B",
            "judge_winner": winner, "judge_reason": reason,
        })

    # answer key
    (OUT / "answer_key.json").write_text(json.dumps(rows, ensure_ascii=False, indent=2), encoding="utf-8")

    # blind scoring sheet
    sheet = ["# تستِ کورِ فاز ۱ — کدام جواب را راحت‌تر می‌فرستی؟", "",
             "برای هر مورد فقط A یا B را علامت بزن. نمی‌دانی کدام محصول است.", ""]
    for r in rows:
        sheet += [f"## مورد {r['i']}", f"**پیام دریافتی:** {r['message']}", "",
                  f"- **A:** {r['A']}", f"- **B:** {r['B']}", "", "انتخاب: ☐ A ☐ B", "", "---", ""]
    (OUT / "scoring_sheet.md").write_text("\n".join(sheet), encoding="utf-8")

    # llm judge tally
    prod_wins = sum(1 for r in rows if r["judge_winner"] == r["product_side"])
    base_wins = sum(1 for r in rows if r["judge_winner"] in ("A", "B") and r["judge_winner"] != r["product_side"])
    ties = len(rows) - prod_wins - base_wins
    decided = prod_wins + base_wins
    rate = (prod_wins / decided) if decided else 0.0
    jr = [f"# قاضیِ خودکار (مدل: {JUDGE_MODEL}) — سیگنالِ مقدماتی", "",
          f"- محصول برد: **{prod_wins}** / ChatGPT خام برد: **{base_wins}** / مساوی: **{ties}**",
          f"- نرخِ برتریِ محصول (بینِ موارد قطعی): **{rate*100:.0f}%**  (شرطِ دروازه: ۷۰٪)",
          f"- حکم: {'✅ عبور (سیگنال)' if rate >= 0.7 else '❌ هنوز نه (سیگنال)'}", "",
          "> این فقط سیگنالِ یک قاضیِ ماشینی است؛ دروازه‌ی واقعی قضاوتِ ۱۰ فارسی‌زبان است.", "",
          "| # | هدف | برنده | محصول کدام بود | دلیلِ قاضی |", "| :- | :- | :- | :- | :- |"]
    for r in rows:
        jr.append(f"| {r['i']} | {r['goal']} | {r['judge_winner']} | {r['product_side']} | {r['judge_reason']} |")
    (OUT / "llm_judge_results.md").write_text("\n".join(jr), encoding="utf-8")

    print(f"\nDONE. product {prod_wins} / baseline {base_wins} / tie {ties} -> product preference {rate*100:.0f}%")
    print(f"Files in {OUT}")


if __name__ == "__main__":
    asyncio.run(main())
