from __future__ import annotations

from dataclasses import dataclass
import json
import re
from typing import Any

import httpx

from app.config import get_settings
from app.schemas import FreeDecodeIn, FreeDecodeOutput, LensLabel, PaidDecodeOutput, ReplyOption, SafetyOutput
from app.utils import has_sensitive_info


PROMPT_VERSION = "message-decoder-system-v0.1"
MODEL_VERSION = "mock-v0.1"

SYSTEM_PROMPT = """
تو Message Decoder by NeuroLens هستی؛ یک ابزار فارسی‌زبان برای رمزگشایی پیام‌ها، چت‌ها و ایمیل‌های مبهم، سرد، تند، احساسی، کنایه‌آمیز یا حرفه‌ای.

هدف تو این است که قبل از اینکه کاربر جواب بدهد، به او کمک کنی بفهمد پشت پیام طرف مقابل چه نیاز، ترس، فشار، سوءتفاهم یا حساسیتی پنهان است و بعد مسیر پاسخ کم‌ریسک‌تر را پیشنهاد بدهی.

تو روان‌درمانگر، پزشک، تشخیص‌دهنده اختلال، ذهن‌خوان یا قاضی نیت قطعی آدم‌ها نیستی. از روی یک پیام نمی‌توانی سطح واقعی هورمون، اختلال شخصیت، نیت قطعی یا سلامت روان کسی را تشخیص بدهی.

سه هورمون در این محصول فقط به عنوان لنز رفتاری و روان‌زیستی استفاده می‌شوند، نه به عنوان تشخیص زیستی واقعی:
۱. هدف و کنترل — Dopamine Lens
۲. امنیت و اعتماد — Oxytocin Lens
۳. شأن و احترام — Serotonin Lens

هرگز نگو اکسی‌توسین طرف پایین است، دوپامین طرف بالاست، این آدم اختلال دارد، این فرد narcissist است، یا قطعاً قصدش کنترل است.
به جای آن از «احتمالاً»، «ممکن است»، «نشانه‌هایی از» و «برداشت محتاطانه» استفاده کن.
اگر پیام خطرناک است، safety-first باش. اگر کاربر درخواست کنترل، guilt-trip یا آسیب کرد، به پاسخ سالم و قاطع redirect کن.
خروجی باید فارسی طبیعی، قابل نمایش در UI، و JSON معتبر مطابق schema خواسته‌شده باشد.
""".strip()


LENSES = {
    "dopamine": LensLabel(fa="هدف و کنترل", en="Dopamine Lens", key="dopamine"),
    "oxytocin": LensLabel(fa="امنیت و اعتماد", en="Oxytocin Lens", key="oxytocin"),
    "serotonin": LensLabel(fa="شأن و احترام", en="Serotonin Lens", key="serotonin"),
}


@dataclass
class Classification:
    safety_label: str
    dominant_lens: str
    secondary_lenses: list[str]
    confidence: str
    manipulative: bool = False


SAFETY_TERMS = [
    "میام دم خونتون",
    "میام دم خونه",
    "می‌کشمت",
    "میکشمت",
    "خودمو میکشم",
    "خودم را می‌کشم",
    "آبروریزی",
    "تهدید",
    "لو میدم",
    "پخش می‌کنم",
]
MANIPULATION_TERMS = ["حس گناه", "کنترلش کنم", "برگرده", "ضربه بزنم", "وابسته‌اش کنم"]
DOPAMINE_TERMS = ["چرا هنوز", "تا امشب", "قرار بود", "پیگیری", "انجامش ندادی", "منتظر", "مشخصش کن"]
OXYTOCIN_TERMS = ["برات مهم نیست", "هر جور راحتی", "تنها", "دوستم نداری", "بی‌اهمیت", "seen", "سین"]
SEROTONIN_TERMS = ["ارزش", "احترام", "فقط خودت", "خرابم کردی", "حق با توئه", "کم نذاشتم", "تحقیر"]


def classify(payload: FreeDecodeIn) -> Classification:
    combined = f"{payload.message_text}\n{payload.optional_context or ''}".lower()
    if any(term in combined for term in SAFETY_TERMS):
        return Classification("high_risk", "serotonin", [], "بالا")

    manipulative = any(term in combined for term in MANIPULATION_TERMS)
    scores = {
        "dopamine": sum(term in combined for term in DOPAMINE_TERMS),
        "oxytocin": sum(term in combined for term in OXYTOCIN_TERMS),
        "serotonin": sum(term in combined for term in SEROTONIN_TERMS),
    }
    goal_bias = {
        "professional_reply": "dopamine",
        "make_them_accountable": "dopamine",
        "avoid_needy": "oxytocin",
        "set_boundary": "serotonin",
        "end_conversation": "serotonin",
    }.get(payload.user_goal)
    if goal_bias:
        scores[goal_bias] += 1

    dominant = max(scores, key=scores.get)
    if scores[dominant] == 0:
        dominant = "oxytocin" if payload.relationship_type in ("romantic", "ex", "family") else "dopamine"

    secondary = [key for key, value in scores.items() if key != dominant and value > 0]
    confidence = "بالا" if scores[dominant] >= 2 else "متوسط"
    return Classification("manipulation_redirect" if manipulative else "normal", dominant, secondary, confidence, manipulative)


def safety_output() -> SafetyOutput:
    return SafetyOutput(
        warning_title="هشدار امنیتی",
        priority="اولویت اینجا آرام کردن رابطه نیست؛ اولویت حفظ امنیت، مستندسازی و کمک گرفتن از فرد قابل اعتماد یا مرجع مناسب است.",
        suggested_reply="این لحن برای من قابل قبول نیست. اگر حرفی هست، فقط در فضای محترمانه و امن پاسخ می‌دهم.",
        recommendation="اگر احساس خطر فوری داری، تنها نمان و از فرد قابل اعتماد یا مرجع اضطراری کمک بگیر.",
    )


def free_decode(payload: FreeDecodeIn, classification: Classification) -> FreeDecodeOutput:
    if _use_ai_provider():
        ai_output = _free_decode_with_ai(payload, classification)
        if ai_output is not None:
            return ai_output

    lens = LENSES[classification.dominant_lens]
    explanations = {
        "dopamine": "این لنز یعنی پیام بیشتر حول نتیجه، زمان‌بندی، کنترل شرایط و رسیدن به خروجی مشخص می‌چرخد.",
        "oxytocin": "این لنز یعنی پیام بیشتر حول نیاز به اطمینان، اعتماد، نزدیکی یا ترس از بی‌اهمیت شدن می‌چرخد.",
        "serotonin": "این لنز یعنی پیام بیشتر حول احترام، دیده‌شدن، شأن، ارزش یا حفظ جایگاه می‌چرخد.",
    }
    why = {
        "dopamine": "در متن نشانه‌هایی از فشار برای نتیجه، پیگیری یا نیاز به پاسخ مشخص دیده می‌شود.",
        "oxytocin": "در متن نشانه‌هایی از فاصله، کنایه، نیاز به اطمینان یا حس دیده‌نشدن دیده می‌شود.",
        "serotonin": "در متن نشانه‌هایی از حساسیت به احترام، ارزش، سرزنش یا حفظ شأن دیده می‌شود.",
    }
    risks = {
        "dopamine": "اگر زیادی توضیح بدهی یا دفاعی جواب بدهی، ممکن است غیرحرفه‌ای یا نامطمئن به نظر برسی.",
        "oxytocin": "اگر سرد، دفاعی یا تحقیرآمیز جواب بدهی، احتمالاً حس طردشدگی یا بی‌اهمیت شدن بیشتر می‌شود.",
        "serotonin": "اگر موضوع را کوچک کنی یا دنبال بردن بحث بروی، مکالمه ممکن است وارد دعوای شأن و قدرت شود.",
    }
    directions = {
        "dopamine": "مسئولیت را کوتاه روشن کن، وضعیت فعلی را بگو و زمان یا اقدام مشخص بده.",
        "oxytocin": "اول احساس را ببین، بعد نیتت را روشن کن، بعد اگر لازم بود توضیح بده.",
        "serotonin": "احترام را برگردان، سهم خودت را روشن کن و بدون تحقیر مرز بگذار.",
    }
    needs = {
        "dopamine": "احتمالاً نیاز پشت پیام، شفافیت، نتیجه، کنترل زمان‌بندی یا پاسخ مشخص است.",
        "oxytocin": "احتمالاً نیاز پشت پیام، اطمینان، دیده‌شدن یا کمتر حس کردن فاصله است.",
        "serotonin": "احتمالاً نیاز پشت پیام، احترام، ارزش دیده‌شدن یا حفظ شأن است.",
    }
    if classification.manipulative:
        needs[classification.dominant_lens] = "درخواست فعلی رنگ کنترل یا فشار روانی دارد؛ مسیر سالم‌تر این است که احساس و مرزت را واضح بگویی، نه اینکه حس گناه بسازی."

    return FreeDecodeOutput(
        dominant_lens=lens,
        dominant_lens_explanation=explanations[classification.dominant_lens]
        + " این به معنی بالا یا پایین بودن واقعی هورمون طرف مقابل نیست؛ فقط یک لنز رفتاری برای خواندن پیام است.",
        why_this_lens=why[classification.dominant_lens],
        secondary_lenses=[LENSES[key] for key in classification.secondary_lenses],
        likely_underlying_need=needs[classification.dominant_lens],
        conversation_risk=risks[classification.dominant_lens],
        recommended_direction=directions[classification.dominant_lens],
        confidence=classification.confidence,  # type: ignore[arg-type]
        alternative_read="ممکن است پیام فقط از خستگی، عجله، دلخوری لحظه‌ای یا سبک بیان غیرمستقیم آمده باشد.",
        privacy_warning="برای امنیت، بهتر است اطلاعات شخصی مثل شماره، آدرس یا نام کامل را حذف کنی." if has_sensitive_info(payload.message_text) else None,
        cta="برای همین موقعیت، ۳ پاسخ آماده بساز: نرم، مرزبردار و کوتاه.",
    )


def paid_decode(free_output: FreeDecodeOutput, relationship_type: str, user_goal: str) -> PaidDecodeOutput:
    if _use_ai_provider():
        ai_output = _paid_decode_with_ai(free_output, relationship_type, user_goal)
        if ai_output is not None:
            return ai_output

    professional = relationship_type in ("manager_colleague", "customer") or user_goal == "professional_reply"
    if professional:
        replies = [
            ReplyOption(label="حرفه‌ای", text="حق با شماست، باید زودتر اطلاع می‌دادم. نسخه فعلی را تا ساعت ۴ امروز ارسال می‌کنم و از این به بعد وضعیت کار را قبل از موعد گزارش می‌دهم.", why_it_works="مسئولیت را می‌پذیرد، زمان دقیق می‌دهد و دفاع اضافه ندارد."),
            ReplyOption(label="کوتاه", text="بله، تأخیر از سمت من بوده. گزارش تا ساعت ۴ امروز ارسال می‌شود.", why_it_works="شفاف، کوتاه و نتیجه‌محور است."),
            ReplyOption(label="مرزبردار", text="متوجه‌ام که زمان‌بندی مهم بوده. برای اینکه مسیر روشن باشد، نسخه فعلی را تا ساعت ۴ می‌فرستم و اگر اصلاحی لازم بود همان‌جا مشخص می‌کنیم.", why_it_works="هم نگرانی طرف را می‌بیند، هم مسیر کار را کنترل‌پذیر می‌کند."),
        ]
        words = ["سرم شلوغ بود", "فکر کردم عجله‌ای نیست", "داشتم روش کار می‌کردم دیگه"]
        opening = "حق با شماست، زمان‌بندی باید بهتر مدیریت می‌شد."
    else:
        replies = [
            ReplyOption(label="نرم", text="می‌فهمم چرا اینطوری برداشت کردی. قصدم این نبود که حس کنی برام مهم نیستی. نمی‌خوام بحث رو بدتر کنم؛ می‌خوام درست‌تر توضیح بدم.", why_it_works="اول احساس را می‌بیند و بعد نیت را روشن می‌کند."),
            ReplyOption(label="مرزبردار", text="می‌فهمم ناراحت شدی، ولی دوست ندارم با کنایه ادامه بدیم. اگه مستقیم بگی چی اذیتت کرده، من هم بهتر می‌تونم جواب بدم.", why_it_works="هم ناراحتی را نادیده نمی‌گیرد، هم الگوی کنایه را تقویت نمی‌کند."),
            ReplyOption(label="کوتاه", text="برام مهمی. فقط نمی‌خوام با سوءتفاهم جواب بدم. بیا مستقیم‌تر حرف بزنیم.", why_it_works="کم‌ریسک، ساده و قابل ارسال است."),
        ]
        words = ["باز", "تو همیشه", "مشکل خودته", "من که کاری نکردم", "هر جور راحتی پس"]
        opening = "می‌فهمم چرا اینطوری برداشت کردی."

    if user_goal == "end_conversation":
        replies.append(
            ReplyOption(
                label="پایان‌دهنده",
                text="حرفت رو شنیدم و نمی‌خوام بی‌احترامی کنم، اما فکر می‌کنم ادامه این مکالمه الان کمکی نمی‌کنه. بهتره اینجا متوقفش کنیم.",
                why_it_works="مرز را روشن می‌کند بدون اینکه تحقیر یا حمله کند.",
            )
        )

    copy_ready = replies[0].text if professional else f"{opening} ولی دوست ندارم با کنایه ادامه بدیم. اگه مستقیم بگی چی اذیتت کرده، بهتر می‌تونم جواب بدم."
    return PaidDecodeOutput(
        deep_read=f"برداشت عمیق‌تر: {free_output.likely_underlying_need} پاسخ بهتر باید هم ریسک مکالمه را کم کند، هم قدرت و مرز تو را نگه دارد.",
        dominant_lens=free_output.dominant_lens,
        secondary_lenses=free_output.secondary_lenses,
        reply_options=replies,
        words_to_avoid=words,
        safe_opening_line=opening,
        copy_ready_reply=copy_ready,
        attribution_reply="برای اینکه دفاعی جواب ندم، پیامت رو با Message Decoder نگاه کردم. برداشتم اینه که شاید پشت پیام یک نیاز یا نگرانی مهم هست. درست می‌فهمم؟",
        follow_up_question="اگر بخواهی بحث را باز کنی، بهتر است بپرسی: دقیقاً کدام بخش حرفم اذیتت کرد؟",
    )


def current_model_version() -> str:
    settings = get_settings()
    if _use_ai_provider():
        return settings.ai_model
    return settings.ai_model_version or MODEL_VERSION


def _use_ai_provider() -> bool:
    settings = get_settings()
    return settings.ai_provider in {"openai", "openai_compatible", "liara"} and bool(settings.ai_api_key)


def _free_decode_with_ai(payload: FreeDecodeIn, classification: Classification) -> FreeDecodeOutput | None:
    schema_hint = {
        "dominant_lens": {"fa": "امنیت و اعتماد", "en": "Oxytocin Lens", "key": "oxytocin"},
        "dominant_lens_explanation": "string",
        "why_this_lens": "string",
        "secondary_lenses": [{"fa": "شأن و احترام", "en": "Serotonin Lens", "key": "serotonin"}],
        "likely_underlying_need": "string",
        "conversation_risk": "string",
        "recommended_direction": "string",
        "confidence": "پایین | متوسط | بالا",
        "alternative_read": "string",
        "privacy_warning": None,
        "cta": "string",
    }
    user_prompt = {
        "task": "free_decode",
        "message_text": payload.message_text,
        "relationship_type": payload.relationship_type,
        "user_goal": payload.user_goal,
        "optional_context": payload.optional_context,
        "rule_based_classification": {
            "safety_label": classification.safety_label,
            "dominant_lens": classification.dominant_lens,
            "secondary_lenses": classification.secondary_lenses,
            "confidence": classification.confidence,
            "manipulative": classification.manipulative,
        },
        "requirements": [
            "پاسخ آماده کامل نده.",
            "لنز غالب را توضیح بده و تاکید کن تشخیص هورمونی واقعی نیست.",
            "از قطعیت درباره نیت یا شخصیت طرف مقابل پرهیز کن.",
            "فارسی طبیعی بنویس.",
        ],
        "json_schema_shape": schema_hint,
    }
    data = _chat_json(user_prompt)
    if data is None:
        return None
    if has_sensitive_info(payload.message_text) and not data.get("privacy_warning"):
        data["privacy_warning"] = "برای امنیت، بهتر است اطلاعات شخصی مثل شماره، آدرس یا نام کامل را حذف کنی."
    try:
        return FreeDecodeOutput.model_validate(data)
    except Exception:
        return None


def _paid_decode_with_ai(free_output: FreeDecodeOutput, relationship_type: str, user_goal: str) -> PaidDecodeOutput | None:
    schema_hint = {
        "deep_read": "string",
        "dominant_lens": free_output.dominant_lens.model_dump(),
        "secondary_lenses": [lens.model_dump() for lens in free_output.secondary_lenses],
        "reply_options": [
            {"label": "نرم", "text": "string", "why_it_works": "string"},
            {"label": "مرزبردار", "text": "string", "why_it_works": "string"},
            {"label": "کوتاه", "text": "string", "why_it_works": "string"},
        ],
        "words_to_avoid": ["string"],
        "safe_opening_line": "string",
        "copy_ready_reply": "string",
        "attribution_reply": "string",
        "follow_up_question": "string",
    }
    user_prompt = {
        "task": "paid_decode",
        "free_output": free_output.model_dump(),
        "relationship_type": relationship_type,
        "user_goal": user_goal,
        "requirements": [
            "۳ تا ۵ پاسخ آماده و قابل کپی بده.",
            "برای کار لحن حرفه‌ای، برای رابطه لحن انسانی و بدون التماس، برای اکس مرزبردار باشد.",
            "کلمات ممنوع و دلیل هر پاسخ را بده.",
            "نسخه با استناد به Message Decoder اختیاری و نرم باشد.",
            "فارسی طبیعی بنویس، نه رباتی یا بیش از حد روانشناسانه.",
        ],
        "json_schema_shape": schema_hint,
    }
    data = _chat_json(user_prompt)
    if data is None:
        return None
    try:
        return PaidDecodeOutput.model_validate(data)
    except Exception:
        return None


def _chat_json(user_payload: dict[str, Any]) -> dict[str, Any] | None:
    settings = get_settings()
    endpoint = settings.ai_api_base_url.rstrip("/") + "/chat/completions"
    body = {
        "model": settings.ai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "temperature": 0.4,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {settings.ai_api_key}",
        "Content-Type": "application/json",
    }
    try:
        with httpx.Client(timeout=35) as client:
            response = client.post(endpoint, headers=headers, json=body)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return _parse_json_object(content)
    except Exception:
        return None


def _parse_json_object(content: str) -> dict[str, Any] | None:
    try:
        value = json.loads(content)
        return value if isinstance(value, dict) else None
    except json.JSONDecodeError:
        match = re.search(r"\{.*\}", content, flags=re.DOTALL)
        if not match:
            return None
        try:
            value = json.loads(match.group(0))
            return value if isinstance(value, dict) else None
        except json.JSONDecodeError:
            return None
