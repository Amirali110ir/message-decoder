from __future__ import annotations

import asyncio
import hashlib
import json
import logging
import re
from typing import Any

import httpx

from app.config import get_settings
from app.schemas import FreeDecodeIn, FreeDecodeOutput, LensLabel, LensMix, PaidDecodeOutput, ReactionForecast, ReplyOption, SafetyOutput, ToneStress
from app.services.cache import get_cached_response, set_cached_response
from app.services.golden_examples import golden_examples_as_messages, golden_examples_for_prompt
from app.services.rule_engine import (
    RULE_ENGINE_VERSION,
    Classification,
    classification_payload,
    classify,
    paid_reply_playbook,
)
from app.utils import has_sensitive_info


PROMPT_VERSION = "message-decoder-system-v0.4"
MODEL_VERSION = "mock-v0.1"

logger = logging.getLogger(__name__)

# Retry delays (seconds) for transient AI API failures.
_AI_RETRY_DELAYS: tuple[int, ...] = (2, 4)
OUTPUT_SCHEMA_VERSION = "decode-schema-v0.4"


class PaidDecodeUnavailable(Exception):
    pass


SYSTEM_PROMPT = """
تو Message Decoder by NeuroLens هستی؛ یک ابزار فارسی‌زبان برای رمزگشایی پیام‌ها، چت‌ها و ایمیل‌های مبهم، سرد، تند، احساسی، کنایه‌آمیز یا حرفه‌ای.

وعده محصول: قبل از جواب دادن، بفهم پشت پیام طرف چیست و یک جواب کم‌ریسک‌تر بساز.
هدف اول: فهمیدن نیاز، ترس، فشار، سوءتفاهم یا ریسک پنهان پشت پیام طرف مقابل.
هدف دوم: ساختن پاسخی که کاربر بتواند بی‌دردسر بفرستد — انسانی، کم‌ریسک، و صادقانه.

══════ محدودیت‌های همیشگی ══════
- از روی متن، سطح واقعی هورمون تشخیص نده. هیچ‌وقت نگو «اکسی‌توسین/سروتونین/دوپامینِ طرف بالا/پایین است». سه هورمون فقط لنز رفتاری‌اند، نه واقعیت زیستی.
- تشخیص روانشناختی، پزشکی یا شخصیتی نده. برچسب‌هایی مثل narcissist، toxic، bipolar، اختلال شخصیت، افسرده، وابسته یا کنترل‌گر را به‌عنوان حکم قطعی نده.
- درباره نیت طرف مقابل قطعی حرف نزن؛ از «احتمالاً»، «ممکن است»، «به‌نظر می‌رسد» استفاده کن.

══════ سه لنز اصلی (زبان داخلیِ تحلیل) ══════
۱. لنز هدف و کنترل — Dopamine Lens: هدف، نتیجه، کنترل، عجله، ناکامی، فشار برای اقدام. سؤال پنهان: «چرا چیزی که می‌خوام جلو نمی‌ره؟»
۲. لنز امنیت و اعتماد — Oxytocin Lens: امنیت عاطفی، اعتماد، نزدیکی، دیده‌شدن، ترس از بی‌اهمیت شدن. سؤال پنهان: «هنوز برات مهمم و می‌تونم بهت اعتماد کنم؟»
۳. لنز شأن و احترام — Serotonin Lens: شأن، احترام، جایگاه، تحقیر، مقایسه، قضاوت. سؤال پنهان: «دیده شدم و جایگاهم حفظ شد؟»

══════ فرآیند ══════
۱. اول خطر را بررسی کن. اگر تهدید، خشونت، خودآسیب‌رسانی، اخاذی، stalking، اجبار یا تهدید جنسی/فیزیکی بود، Safety Mode فعال است و پاسخ عاطفی یا استراتژیکِ عادی تولید نکن.
۲. لحن پیام را بخوان (سرد، تند، کنایه، منفعل-پرخاشگر، قربانی‌گونه، کنترل‌گر، مبهم، دفاعی...).
۳. لنز غالب و فرعی را انتخاب کن و نیاز پنهان، ریسک پاسخ غلط، جهت پاسخ بهتر و برداشت جایگزین را دربیاور.
۴. اگر درخواست کاربر manipulative بود، آن را به یک پاسخ سالم، قاطع و بالغ تبدیل کن — نه ساختن حس گناه در طرف مقابل.

══════ قواعدِ نوشتنِ «متنِ پاسخِ قابل‌ارسال» ══════
این قواعد فقط برای متن‌هایی است که کاربر عیناً می‌فرستد: reply_options[].text، copy_ready_reply، safe_opening_line و هر بازنویسی. (متنِ تحلیل لازم نیست شکسته باشد، ولی آن هم روان و انسانی باشد.)

فرم (شکلِ جمله):
- شکسته بنویس: «می‌خوام» نه «می‌خواهم»، «بهت» نه «به تو»، «نمی‌دونم» نه «نمی‌دانم».
- کوتاه: اندازه‌ی یک پیامِ چت، یک تا سه جمله. نه پاراگراف.
- مستقیم سرِ اصل مطلب، مثل پیام تلگرام. بدون مقدمه‌ی «سلام، امیدوارم خوب باشی».
- خطاب صمیمی «تو» (در رابطه/دوست/خانواده/اکس). برای کار و مشتری «شما».
- اتصال‌های حسی («خب»، «راستش»، «آخه») کم و طبیعی، نه پشت‌سرهم.
- هیچ واژه‌ی روان‌شناسی یا کلیشه‌ی درمانی در متنِ پاسخ نیار: «اعتبارسنجی»، «مرزبندی»، «نیاز عاطفی»، «مکانیزم دفاعی»، «فضای امن»، «انرژی»، «ولیدیت کردن»، «ارتباط مؤثر» — هیچ‌کدام.

محتوا (آنچه جمله می‌گوید):
- اول حال را تنظیم کن، بعد منطق: جمله‌ی اول باید حسِ تهدید را خاموش کند، نه استدلال بیاورد.
- تأیید احساس ≠ تأیید ادعا: «می‌فهمم چرا دلخور شدی» آره؛ «حق با توئه» نه (مگر واقعاً سهمی داری).
- مشخص، نه کلی: «جمعه عصر فقط مالِ خودته» بهتر از «بعداً جبران می‌کنم».
- بدونِ دفاع و بهانه: اتهام را آرام نادیده بگیر، توجیه نکن. هیچ‌وقت «سرم شلوغ بود»، «درگیر کاری بودم»، «حواسم نبود» یا هر بهانه‌ی مشابه ننویس — این‌ها تله‌ی طرف را تأیید می‌کنند و پاسخ را ضعیف می‌کنند.
- قدمِ نرمِ طرف را بگیر: اگر طرف نرم شد یا عذرخواهی کرد، با گرمی بگیرش، خنثی نکن.
- در باز، نه مطالبه: «هر وقت خواستی حرف بزنیم» بهتر از «بگو چی شده».

ساختارِ سه‌جمله‌ایِ پیش‌فرض (مگر موقعیت اقتضا نکند):
  جمله ۱: حسِ تهدید را خاموش کن (تأیید احساس، بدون تأیید ادعا).
  جمله ۲: موضع خودت را مشخص و بدون دفاع بگو (جزئی، نه کلی).
  جمله ۳: یک در باز بگذار (دعوت، نه دستور).

لحنِ پاسخ بر اساس رابطه:
- رابطه عاطفی: انسانی، گرم، واضح، بدون التماس.
- اکس: محترمانه، با مرزِ روشن، بدون باز کردن بی‌دلیلِ رابطه.
- کار و همکار/مشتری: حرفه‌ای، کوتاه، مسئولیت‌پذیر، بدون دفاعِ اضافه (اینجا «شما» و کمی رسمی‌تر).
- خانواده: محترمانه و احساسی اما با مرز.
- دوست: صمیمی، روشن، بدون حمله.

══════ مرزِ اخلاقی (همیشه فعال) ══════
پاسخ باید به کاربر کمک کند صادقانه‌تر و واضح‌تر حرف بزند، نه اینکه طرف مقابل را فریب دهد، گناه‌اندازی کند یا به کاری وادارد که با آگاهیِ کامل انتخاب نمی‌کرد. هیچ پاسخ manipulative، تحقیرآمیز، تهدیدآمیز یا التماس‌گونه نساز.

خروجی باید فارسیِ طبیعی و غیررباتی، و یک JSON معتبر مطابق schema خواسته‌شده باشد.
""".strip()


# Focused, lightweight system prompts for the auxiliary tasks. The full
# SYSTEM_PROMPT (lens framework, decode process, reply structure) is noise for
# these single-purpose calls — it wastes tokens and dilutes the model's
# attention. Each of these keeps only the rules that matter for its task.
TONE_EDIT_SYSTEM_PROMPT = """
تو ویرایشگرِ لحنِ پیام‌های فارسی هستی. یک پیامِ آماده می‌گیری و فقط لحنش را طبقِ خواسته تغییر می‌دهی.

قواعد:
- معنا و موضعِ اصلیِ پیام را عوض نکن؛ فقط لحن و سبک را تغییر بده.
- شکسته و طبیعی بنویس («می‌خوام» نه «می‌خواهم»)، کوتاه و قابلِ ارسال مثلِ پیامِ چت.
- هیچ واژه‌ی روان‌شناسی یا کلیشه‌ی درمانی نیار.
- هیچ پاسخ manipulative، تحقیرآمیز، تهدیدآمیز یا التماس‌گونه نساز.
- خروجی فقط یک JSON معتبر مطابقِ schema خواسته‌شده باشد.
""".strip()

BEFORE_SEND_SYSTEM_PROMPT = """
تو ارزیابِ ریسکِ پیام‌های فارسی هستی. متنی که خودِ کاربر می‌خواهد بفرستد را می‌گیری و ریسکِ واکنشِ منفیِ طرفِ مقابل را می‌سنجی.

قواعد:
- درباره‌ی نیتِ طرفِ مقابل قطعی حرف نزن.
- نقاطِ پرخطر را مشخص نام ببر (لحنِ تند، سرزنشِ مطلق، گناه‌اندازی، ابهام، طولِ زیاد).
- پیشنهادهای کوتاه و عملی برای کم‌ریسک‌تر شدن بده.
- اگر بازنویسی می‌دهی، شکسته، کوتاه و قابلِ ارسال باشد، بدونِ واژه‌ی روان‌شناسی.
- خروجی فقط یک JSON معتبر مطابقِ schema خواسته‌شده باشد.
""".strip()

COMPRESS_SYSTEM_PROMPT = """
تو خلاصه‌سازِ زمینه‌ی گفتگوهای فارسی هستی. یک زمینه‌ی طولانی می‌گیری و آن را به یک خلاصه‌ی کوتاهِ ساختاریافته تبدیل می‌کنی.

قواعد:
- فقط حقایقِ مهم برای فهمِ موقعیت را نگه دار؛ حاشیه و تکرار را دور بریز.
- هیچ تفسیر، قضاوت یا تحلیلی اضافه نکن؛ فقط فشرده کن.
- خروجی فقط یک JSON معتبر مطابقِ schema خواسته‌شده باشد.
""".strip()


LENSES = {
    "dopamine": LensLabel(fa="هدف و کنترل", en="Dopamine Lens", key="dopamine"),
    "oxytocin": LensLabel(fa="امنیت و اعتماد", en="Oxytocin Lens", key="oxytocin"),
    "serotonin": LensLabel(fa="شأن و احترام", en="Serotonin Lens", key="serotonin"),
}


def safety_output() -> SafetyOutput:
    return SafetyOutput(
        warning_title="هشدار امنیتی",
        priority="اولویت اینجا آرام کردن رابطه نیست؛ اولویت حفظ امنیت، مستندسازی و کمک گرفتن از فرد قابل اعتماد یا مرجع مناسب است.",
        suggested_reply="این لحن برای من قابل قبول نیست. اگر حرفی هست، فقط در فضای محترمانه و امن پاسخ می‌دهم.",
        recommendation="اگر احساس خطر فوری داری، تنها نمان و از فرد قابل اعتماد یا مرجع اضطراری کمک بگیر.",
    )


async def free_decode(
    payload: FreeDecodeIn,
    classification: Classification,
    message_focus: str | None = None,
    contact_memory_context: str | None = None,
) -> FreeDecodeOutput:
    if _use_ai_provider():
        ai_output = await _free_decode_with_ai(payload, classification, message_focus, contact_memory_context)
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

    why_text = why[classification.dominant_lens]
    if classification.evidence_terms:
        why_text = f"{why_text} نشانه‌های برجسته: {'، '.join(classification.evidence_terms)}."
    if classification.tones:
        why_text = f"{why_text} لحن احتمالی پیام: {'، '.join(classification.tones)}."

    focus_prefix = f"با توجه به {message_focus}، " if message_focus else ""
    personalization = None
    if contact_memory_context:
        personalization = "این تحلیل با پرونده مخاطب و الگوهای قبلی همین رابطه تنظیم شده است."
    elif message_focus:
        personalization = f"این تحلیل به این موقعیت وصل شده است: {message_focus}."

    return FreeDecodeOutput(
        dominant_lens=lens,
        dominant_lens_explanation=explanations[classification.dominant_lens]
        + " این به معنی بالا یا پایین بودن واقعی هورمون طرف مقابل نیست؛ فقط یک لنز رفتاری برای خواندن پیام است.",
        why_this_lens=f"{focus_prefix}{why_text}" if focus_prefix else why_text,
        message_focus=message_focus,
        personalization_note=personalization,
        secondary_lenses=[LENSES[key] for key in classification.secondary_lenses],
        lens_mix=lens_mix_from_classification(classification),
        tone_stress=tone_stress_from_classification(classification),
        likely_underlying_need=_with_focus(classification.hidden_need or needs[classification.dominant_lens], message_focus),
        conversation_risk=_with_focus(classification.main_risk or risks[classification.dominant_lens], message_focus),
        recommended_direction=_with_focus(classification.recommended_direction or directions[classification.dominant_lens], message_focus),
        confidence=classification.confidence,  # type: ignore[arg-type]
        alternative_read=classification.alternative_interpretation
        or "ممکن است پیام فقط از خستگی، عجله، دلخوری لحظه‌ای یا سبک بیان غیرمستقیم آمده باشد.",
        privacy_warning="برای امنیت، بهتر است اطلاعات شخصی مثل شماره، آدرس یا نام کامل را حذف کنی." if has_sensitive_info(payload.message_text) else None,
        cta="برای همین موقعیت، ۳ پاسخ آماده بساز: نرم، تعیین‌کننده مرز روابط و کوتاه.",
    )


async def paid_decode(
    free_output: FreeDecodeOutput,
    relationship_type: str,
    user_goal: str,
    contact_profile_summary: str | None = None,
    message_text: str | None = None,
    optional_context: str | None = None,
) -> PaidDecodeOutput:
    settings = get_settings()
    message_focus = free_output.message_focus
    if _use_ai_provider():
        ai_output = await _paid_decode_with_ai(
            free_output,
            relationship_type,
            user_goal,
            contact_profile_summary,
            message_text,
            optional_context,
        )
        if ai_output is not None:
            return ai_output
        raise PaidDecodeUnavailable("Paid AI generation is unavailable")
    if settings.is_production:
        raise PaidDecodeUnavailable("Paid AI generation is not configured")

    professional = relationship_type in ("manager_colleague", "customer") or user_goal == "professional_reply"
    is_ex = relationship_type == "ex" or user_goal == "end_conversation"

    if professional:
        replies = [
            ReplyOption(
                label="حرفه‌ای",
                text="متوجه این موضوع هستم و پیگیری شما کاملاً بجاست. این مسئله در حال بررسی است و نتیجه نهایی را تا پایان وقت اداری امروز به شما اطلاع می‌دهم تا طبق برنامه هماهنگ پیش برویم.",
                why_it_works="مسئولیت کاری را تایید می‌کند و بدون بهانه‌تراشی، زمان دقیق پاسخ‌گویی می‌دهد."
            ),
            ReplyOption(
                label="کوتاه",
                text="پیام شما دریافت شد. موضوع در دست بررسی است و نتیجه را تا ساعت ۴ امروز خدمت شما ارسال خواهم کرد.",
                why_it_works="پیام را کوتاه و بدون زیاده‌گویی نگه می‌دارد و بر زمان مشخص متمرکز است."
            ),
            ReplyOption(
                label="تعیین‌کننده مرز روابط",
                text="از پیگیری شما متشکرم. برای اینکه کارها با کیفیت و نظم بهتری جلو برود، در حال انجام کارها طبق اولویت هستیم و تا ساعت ۴ زمان‌بندی جدید را اعلام می‌کنیم.",
                why_it_works="مرز کاری سالمی را بر اساس اولویت‌ها تعیین کرده و جلوی استرس اضافی را می‌گیرد."
            ),
            ReplyOption(
                label="قاطع و آرام",
                text="حق با شماست، اطلاع‌رسانی باید زودتر انجام می‌شد. برای کاهش ابهام، نسخه جدید تا ساعت ۴ امروز آماده و ارسال خواهد شد.",
                why_it_works="سهم خود را در تاخیر می‌پذیرد و اقدام بعدی را با صراحت اعلام می‌کند."
            ),
            ReplyOption(
                label="نرم",
                text="تأخیر پیش‌آمده را کاملاً درک می‌کنم و بابت آن متاسفم. نهایت تلاشم را می‌کنم که تا ساعت ۴ امروز خروجی هماهنگ‌شده را به دست شما برسانم.",
                why_it_works="همدلی صمیمانه‌ای نشان می‌دهد و روی ارائه راه‌حل در کوتاه‌ترین زمان تمرکز دارد."
            )
        ]
        words = ["سرم شلوغ بود", "فکر کردم عجله‌ای نیست", "داشتم روش کار می‌کردم دیگه", "کار پیش اومد"]
        opening = "حق با شماست، زمان‌بندی باید بهتر مدیریت می‌شد."
    elif is_ex:
        replies = [
            ReplyOption(
                label="نرم",
                text="پیامت را خواندم. نمی‌خواهم گفتگو را تند یا احساسی جلو ببرم، اما اگر نکته مشخص یا مسئله جدی وجود دارد، می‌توانیم کوتاه و محترمانه درباره‌اش صحبت کنیم.",
                why_it_works="راه ارتباط متمدنانه را نمی‌بندد اما جلوی کشمکش‌های عاطفی را می‌گیرد."
            ),
            ReplyOption(
                label="تعیین‌کننده مرز روابط",
                text="می‌فهمم که این موضوع برایت حساس است، اما برای حفظ آرامش هر دو نفرمان ترجیح می‌دهم وارد گفتگوهای احساسی طولانی یا رفت‌وبرگشت‌های گذشته نشویم.",
                why_it_works="به وضوح مرز بین رابطه تمام‌شده و بحث‌های عاطفی گذشته را مشخص می‌کند."
            ),
            ReplyOption(
                label="کوتاه",
                text="پیام تو را دریافت کردم. در حال حاضر ترجیح می‌دهم فضا و فاصله‌مان را به شکل محترمانه حفظ کنیم.",
                why_it_works="بسیار کم‌ریسک است و هیچ سیگنال مبهم یا دعوت به گفتگوهای اضافه ارسال نمی‌کند."
            ),
            ReplyOption(
                label="قاطع و آرام",
                text="حرفت را شنیدم و قصد بی‌احترامی ندارم، اما فکر می‌کنم ادامه دادن این مکالمه در حال حاضر کمکی به ما نمی‌کند و بهتر است در همین‌جا متوقفش کنیم.",
                why_it_works="قاطعانه و با احترام کامل مکالمه فرسایشی را به پایان می‌رساند."
            )
        ]
        words = ["دلم برات تنگ شده", "تو همیشه همین بودی", "برگرد", "بذار ثابت کنم", "هر چی تو بگی"]
        opening = "حرفت رو فهمیدم."
    else:
        replies = [
            ReplyOption(
                label="نرم",
                text="می‌فهمم چرا اینطوری برداشت کردی و اصلاً دوست ندارم حس کنی برام مهم نیستی. قصدم آسیب زدن یا ایجاد فاصله نبوده و دلم می‌خواد سوءتفاهم‌ها رو با هم برطرف کنیم.",
                why_it_works="اول احساس را اعتبار می‌بخشد و صمیمیت را ترمیم می‌کند بدون اینکه التماس کند."
            ),
            ReplyOption(
                label="تعیین‌کننده مرز روابط",
                text="می‌فهمم ناراحت یا دلخوری، ولی دوست ندارم با کنایه یا غیرمستقیم با هم صحبت کنیم. اگر بدون قضاوت و مستقیم بگی چی اذیتت کرده، من هم روشن‌تر می‌تونم جواب بدم.",
                why_it_works="هم احساس طرف مقابل را می‌بیند و هم الگوی کنایه‌آمیز گفتگو را به چالش می‌کشد."
            ),
            ReplyOption(
                label="کوتاه",
                text="رابطه‌مون و خودت برام خیلی مهمی. بیا اجازه ندیم سوءتفاهم‌ها بینمون فاصله بندازه و مستقیم‌تر حرف بزنیم.",
                why_it_works="ساده، صمیمی و کم‌ریسک است و برای کپی کردن بسیار مناسب است."
            ),
            ReplyOption(
                label="قاطع و آرام",
                text="دوست دارم منظورت رو دقیق بفهمم، اما با لحن مبهم یا کنایه این کار سخت میشه. اگر با آرامش بگی چی شده، من کاملاً آماده شنیدنم.",
                why_it_works="با وقار و قاطعیت، طرف مقابل را به یک گفتگوی بالغانه و بدون تنش دعوت می‌کند."
            )
        ]
        words = ["باز شروع کردی", "تو همیشه حساسی", "مشکل خودته", "من که کاری نکردم", "هر جور راحتی پس"]
        opening = "می‌فهمم چرا اینطوری برداشت کردی."

    if user_goal == "end_conversation":
        replies.append(
            ReplyOption(
                label="پایان‌دهنده",
                text="حرفت رو شنیدم و نمی‌خوام بی‌احترامی کنم، اما فکر می‌کنم ادامه این مکالمه الان کمکی نمی‌کنه. بهتره اینجا متوقفش کنیم.",
                why_it_works="مرز را روشن می‌کند بدون اینکه تحقیر یا حمله کند.",
            )
        )
    replies = with_reaction_predictions(replies, relationship_type, free_output.dominant_lens.key)
    if message_focus:
        replies = _personalize_replies_for_focus(replies, message_focus, professional)

    if user_goal == "set_boundary":
        copy_ready = replies[1].text if len(replies) > 1 else replies[0].text
    elif user_goal == "end_conversation":
        copy_ready = replies[-1].text
    elif message_focus:
        copy_ready = replies[0].text
    else:
        copy_ready = replies[0].text if professional or relationship_type == "ex" else f"{opening} ولی دوست ندارم با کنایه ادامه بدیم. اگه مستقیم بگی چی اذیتت کرده، بهتر می‌تونم جواب بدم."

    return PaidDecodeOutput(
        deep_read=f"برداشت عمیق‌تر: {free_output.likely_underlying_need} پاسخ بهتر باید هم ریسک مکالمه را کم کند، هم قدرت و مرز تو را نگه دارد.",
        dominant_lens=free_output.dominant_lens,
        secondary_lenses=free_output.secondary_lenses,
        personalization_note=_paid_personalization_note(message_focus, contact_profile_summary),
        reply_options=replies,
        words_to_avoid=words,
        safe_opening_line=opening,
        copy_ready_reply=copy_ready,
        attribution_reply="برای اینکه دفاعی جواب ندم، پیامت رو با Message Decoder نگاه کردم. برداشتم اینه که شاید پشت پیام یک نیاز یا نگرانی مهم هست. درست می‌فهمم؟",
        follow_up_question="اگر بخواهی بحث را باز کنی، بهتر است بپرسی: دقیقاً کدام بخش حرفم اذیتت کرد؟",
    )


TONE_LABELS: dict[str, str] = {
    "softer": "نرم‌تر",
    "firmer": "قاطع‌تر",
    "shorter": "کوتاه‌تر",
    "warmer": "گرم‌تر",
    "formal": "رسمی‌تر",
}

_TONE_GUIDE: dict[str, str] = {
    "softer": "همان معنا را با لحن نرم‌تر، کم‌تنش‌تر و همدلانه‌تر بازنویسی کن، بدون اینکه التماس یا ضعف نشان دهد.",
    "firmer": "همان معنا را قاطع‌تر و با مرز روشن‌تر بازنویسی کن، اما بدون تحقیر، تهدید یا پرخاش.",
    "shorter": "همان پیام را خیلی کوتاه‌تر و موجزتر بنویس؛ فقط هسته اصلی پیام بماند.",
    "warmer": "همان پیام را گرم‌تر، صمیمی‌تر و انسانی‌تر بازنویسی کن، بدون اینکه غیرحرفه‌ای شود.",
    "formal": "همان پیام را رسمی‌تر و حرفه‌ای‌تر بازنویسی کن؛ از واژگان محترمانه و ساختار مرتب استفاده کن.",
}


async def tone_edit(
    reply_text: str,
    target_tone: str,
    relationship_type: str,
    user_goal: str,
    original_message: str | None = None,
) -> str:
    if _use_ai_provider():
        ai_text = await _tone_edit_with_ai(reply_text, target_tone, relationship_type, user_goal, original_message)
        if ai_text:
            return ai_text
    return _tone_edit_fallback(reply_text, target_tone)


def _tone_edit_fallback(reply_text: str, target_tone: str) -> str:
    text = reply_text.strip()
    if target_tone == "shorter":
        parts = re.split(r"(?<=[.؟!\n])\s+", text)
        core = next((p.strip() for p in parts if p.strip()), text)
        return core
    if target_tone == "softer":
        return f"می‌دونم موضوع حساسه و نمی‌خوام تند باشم. {text}"
    if target_tone == "firmer":
        return f"می‌خوام روشن و محکم بگم: {text} این برای من مهمه و همین‌طور می‌مونه."
    if target_tone == "warmer":
        return f"تو و رابطه‌مون برام مهمی. {text}"
    if target_tone == "formal":
        return f"با احترام، {text} پیشاپیش از توجه شما سپاس‌گزارم."
    return text


async def _tone_edit_with_ai(
    reply_text: str,
    target_tone: str,
    relationship_type: str,
    user_goal: str,
    original_message: str | None,
) -> str | None:
    user_prompt = {
        "task": "tone_edit",
        "reply_text": reply_text,
        "target_tone": target_tone,
        "tone_instruction": _TONE_GUIDE.get(target_tone, ""),
        "relationship_type": relationship_type,
        "user_goal": user_goal,
        "original_message": original_message,
        "requirements": [
            "فقط لحن و سبک را تغییر بده؛ معنا و موضع اصلی پیام را عوض نکن.",
            "خروجی باید یک پیام فارسی طبیعی و قابل ارسال باشد.",
            "هیچ پاسخ manipulative، تحقیرآمیز، تهدیدآمیز یا التماس‌گونه نساز.",
            "فقط JSON با کلید text برگردان.",
        ],
        "json_schema_shape": {"text": "string"},
    }
    data = await _chat_json(user_prompt, model=_model_for_task("free"), system_prompt=TONE_EDIT_SYSTEM_PROMPT)
    if not data:
        return None
    text = data.get("text")
    return text.strip() if isinstance(text, str) and text.strip() else None


_BEFORE_SEND_BLAME = ["همیشه", "هیچوقت", "هیچ‌وقت", "هیچ وقت", "مشکل خودته", "تو مقصری", "تقصیر توئه", "عین همیشه", "بازم که"]
_BEFORE_SEND_HARSH = ["خفه", "احمق", "بی‌شعور", "مزخرف", "حالم بهم", "متنفر", "گمشو", "لعنت"]


async def before_send_check(
    draft_text: str,
    relationship_type: str,
    user_goal: str,
    original_message: str | None = None,
):
    from app.schemas import BeforeSendOut

    if _use_ai_provider():
        ai_output = await _before_send_with_ai(draft_text, relationship_type, user_goal, original_message)
        if ai_output is not None:
            return ai_output
    return _before_send_fallback(draft_text, relationship_type, user_goal)


def _before_send_fallback(draft_text: str, relationship_type: str, user_goal: str):
    from app.schemas import BeforeSendOut, FreeDecodeIn

    draft = draft_text.strip()
    classification = classify(
        FreeDecodeIn(message_text=draft, relationship_type=relationship_type, user_goal=user_goal)  # type: ignore[arg-type]
    )
    tone = tone_stress_from_classification(classification)
    score = min(tone.intensity, 90)
    flags: list[str] = []
    suggestions: list[str] = []

    if classification.manipulative:
        score += 18
        flags.append("پیام رنگ فشار روانی یا گناه‌اندازی دارد.")
        suggestions.append("به‌جای ساختن حس گناه، احساس و نیاز خودت را مستقیم بگو.")

    blame_hits = [w for w in _BEFORE_SEND_BLAME if w in draft]
    if blame_hits:
        score += 15
        flags.append("کلمات مطلق یا سرزنش‌گر دارد: " + "، ".join(blame_hits[:3]) + ".")
        suggestions.append("به‌جای «همیشه/هیچوقت»، به همین موقعیت مشخص اشاره کن.")

    harsh_hits = [w for w in _BEFORE_SEND_HARSH if w in draft]
    if harsh_hits:
        score += 30
        flags.append("لحن توهین‌آمیز یا پرخاشگر دارد.")
        suggestions.append("کلمات تند را حذف کن؛ پیام تند معمولاً جواب تند می‌گیرد.")

    if "؟" not in draft and len(draft) > 220:
        suggestions.append("پیام طولانی است؛ کوتاه‌تر و روشن‌تر کردنش ریسک سوءتفاهم را کم می‌کند.")

    score = max(0, min(score, 100))
    if score >= 65:
        level = "زیاد"
    elif score >= 35:
        level = "متوسط"
    else:
        level = "کم"

    if not flags:
        flags.append("نشانه پرخطر آشکاری دیده نشد.")
    if not suggestions:
        suggestions.append("لحن متعادل به نظر می‌رسد؛ قبل از ارسال یک بار از نگاه طرف مقابل بخوانش.")

    improved = None
    if level != "کم":
        improved = _tone_edit_fallback(draft, "softer")

    summary = {
        "کم": "این پیام احتمالاً کم‌ریسک است و می‌تواند ارسال شود.",
        "متوسط": "این پیام چند نقطه قابل بهبود دارد؛ پیش از ارسال یک‌بار بازنگری کن.",
        "زیاد": "این پیام ریسک واکنش منفی بالایی دارد؛ بهتر است قبل از ارسال نرم‌ترش کنی.",
    }[level]

    return BeforeSendOut(
        risk_level=level,  # type: ignore[arg-type]
        risk_score=score,
        summary=summary,
        flags=flags,
        suggestions=suggestions,
        improved_text=improved,
    )


async def _before_send_with_ai(
    draft_text: str,
    relationship_type: str,
    user_goal: str,
    original_message: str | None,
):
    from app.schemas import BeforeSendOut

    schema_hint = {
        "risk_level": "کم | متوسط | زیاد",
        "risk_score": 0,
        "summary": "string",
        "flags": ["string"],
        "suggestions": ["string"],
        "improved_text": "string | null",
    }
    user_prompt = {
        "task": "before_send",
        "draft_text": draft_text,
        "original_message": original_message,
        "relationship_type": relationship_type,
        "user_goal": user_goal,
        "requirements": [
            "این متنی است که خود کاربر می‌خواهد بفرستد؛ ریسک واکنش منفی طرف مقابل را ارزیابی کن.",
            "risk_score بین ۰ تا ۱۰۰ و risk_level یکی از کم/متوسط/زیاد باشد و با هم سازگار باشند.",
            "flags: نقاط پرخطر مشخص مثل لحن تند، سرزنش مطلق، گناه‌اندازی، ابهام یا طول زیاد.",
            "suggestions: پیشنهادهای کوتاه و عملی برای کم‌ریسک‌تر کردن پیام.",
            "اگر ریسک متوسط یا زیاد بود، improved_text یک بازنویسی کم‌ریسک‌تر و قابل ارسال بده؛ وگرنه null.",
            "قطعی درباره نیت طرف مقابل حرف نزن و فارسی طبیعی بنویس.",
        ],
        "json_schema_shape": schema_hint,
    }
    data = await _chat_json(user_prompt, model=_model_for_task("free"), system_prompt=BEFORE_SEND_SYSTEM_PROMPT)
    if data is None:
        return None
    try:
        return BeforeSendOut.model_validate(data)
    except Exception:
        return None


# Defensive excuses and clinical jargon that must never survive in a reply the
# user sends. These complement the model-generated words_to_avoid list so the
# post-generation inspector catches content the model sometimes slips in even
# when the system prompt forbids it.
DEFENSIVE_EXCUSE_PHRASES = [
    "سرم شلوغ بود",
    "سرم شلوغه",
    "درگیر کاری بودم",
    "درگیر یه کاری بودم",
    "درگیر کار بودم",
    "حواسم نبود",
    # NOTE: phrases like "یادم رفت" / "فراموش کردم" are intentionally NOT here —
    # they are too context-dependent ("یه چیزی یادم رفت بگم" is innocent), so a
    # substring block would false-positive. The self-critique pass catches
    # genuinely defensive uses instead.
]
PSYCH_JARGON_PHRASES = [
    "اعتبارسنجی",
    "مرزبندی",
    "نیاز عاطفی",
    "مکانیزم دفاعی",
    "فضای امن",
    "ولیدیت",
    "ارتباط مؤثر",
    "ارتباط موثر",
]


def _paid_reply_texts(data: dict[str, Any]) -> list[str]:
    """Collect every text field of a paid output that the user might send."""
    texts: list[str] = []
    for reply in data.get("reply_options") or []:
        if isinstance(reply, dict) and isinstance(reply.get("text"), str):
            texts.append(reply["text"])
    for key in ("copy_ready_reply", "safe_opening_line"):
        value = data.get(key)
        if isinstance(value, str):
            texts.append(value)
    return texts


def find_forbidden_phrases(texts: list[str], words_to_avoid: list[str]) -> list[str]:
    """Return the forbidden phrases that actually appear in any reply text.

    Combines the rule-engine / model words_to_avoid with the built-in defensive
    excuse and psychology-jargon blocklists. Matching is plain substring on the
    raw text (phrases are short colloquial fragments, so this is sufficient and
    avoids false negatives from tokenisation).
    """
    blob = "\n".join(texts)
    candidates = [*(words_to_avoid or []), *DEFENSIVE_EXCUSE_PHRASES, *PSYCH_JARGON_PHRASES]
    seen: list[str] = []
    for phrase in candidates:
        if isinstance(phrase, str) and phrase.strip() and phrase in blob and phrase not in seen:
            seen.append(phrase)
    return seen


def with_reaction_predictions(replies: list[ReplyOption], relationship_type: str, dominant_lens: str) -> list[ReplyOption]:
    fallback = {
        "dopamine": "احتمالاً طرف مقابل سریع‌تر روی اقدام، تصمیم یا پاسخ مشخص تمرکز می‌کند.",
        "oxytocin": "احتمالاً اول دنبال نشانه اطمینان و دیده‌شدن می‌گردد و بعد آرام‌تر توضیح می‌دهد.",
        "serotonin": "احتمالاً به احترام و لحن سنجیده حساس است و اگر شأنش حفظ شود کمتر دفاعی می‌شود.",
    }.get(dominant_lens, "احتمالاً واکنش اولیه به لحن شما وابسته است؛ کوتاه و روشن نگه داشتن پاسخ ریسک را کم می‌کند.")
    if relationship_type in ("manager_colleague", "customer"):
        fallback = "احتمالاً پاسخ حرفه‌ای و زمان‌بندی روشن را بهتر می‌پذیرد و بحث از حالت احساسی خارج می‌شود."

    # Structured forecast per label: firmer/boundary replies carry more risk.
    def _forecast(reply: ReplyOption) -> ReactionForecast:
        firm = reply.label in ("تعیین‌کننده مرز روابط", "قاطع و آرام", "پایان‌دهنده")
        return ReactionForecast(
            likely_reaction="احتمالاً اول کمی جبهه می‌گیرد ولی مرز روشن می‌شود" if firm
            else "احتمالاً آرام‌تر می‌شود چون حسِ متهم‌شدن نمی‌گیرد",
            reason="لحنِ محکم می‌تواند ابتدا دفاعی‌اش کند" if firm
            else "چون اول احساسش دیده می‌شود، کمتر تدافعی می‌شود",
            risk_level="متوسط" if firm else "کم",
        )

    return [
        reply.model_copy(update={
            "reaction_prediction": reply.reaction_prediction or fallback,
            "reaction_forecast": reply.reaction_forecast or _forecast(reply),
        })
        for reply in replies
    ]


def current_model_version(task: str = "free") -> str:
    settings = get_settings()
    if _use_ai_provider():
        return _model_for_task(task)
    return settings.ai_model_version or MODEL_VERSION


def _use_ai_provider() -> bool:
    settings = get_settings()
    return settings.ai_provider in {"openai", "openai_compatible", "liara"} and bool(settings.ai_api_key)


def _model_for_task(task: str) -> str:
    settings = get_settings()
    if task == "paid":
        return settings.ai_paid_model
    return settings.ai_free_model


def lens_mix_from_classification(classification: Classification) -> LensMix:
    scores = {key: max(float(classification.lens_scores.get(key, 0)), 0) for key in LENSES}
    if sum(scores.values()) <= 0:
        scores[classification.dominant_lens] = 1

    total = sum(scores.values())
    raw = {key: (value / total) * 100 for key, value in scores.items()}
    rounded = {key: int(round(value)) for key, value in raw.items()}
    diff = 100 - sum(rounded.values())
    rounded[classification.dominant_lens] = max(0, rounded[classification.dominant_lens] + diff)

    dominant = classification.dominant_lens
    max_key = max(rounded, key=rounded.get)
    if max_key != dominant and rounded[max_key] >= rounded[dominant]:
        delta = rounded[max_key] - rounded[dominant] + 1
        rounded[dominant] += delta
        rounded[max_key] = max(0, rounded[max_key] - delta)
        rebalance = 100 - sum(rounded.values())
        rounded[dominant] += rebalance

    return LensMix(**rounded)


def tone_stress_from_classification(classification: Classification) -> ToneStress:
    tone_weights = {
        "تهدیدکننده": 95,
        "تند": 82,
        "تحقیرکننده": 78,
        "کنترل‌گر": 76,
        "گناه‌دهنده": 72,
        "سرزنش‌گر": 70,
        "منفعل-پرخاشگر": 66,
        "کنایه‌آمیز": 58,
        "دفاعی": 54,
        "قربانی‌گونه": 52,
        "تعیین‌کننده مرز روابط": 46,
        "غمگین": 42,
        "سرد": 40,
        "حسادت‌آمیز": 40,
        "رسمی": 28,
        "مبهم": 34,
    }
    if classification.safety_label == "high_risk":
        return ToneStress(label="پرخطر", intensity=95)
    if not classification.tones:
        return ToneStress()
    label = max(classification.tones, key=lambda tone: tone_weights.get(tone, 35))
    return ToneStress(label=label, intensity=tone_weights.get(label, 35))


async def _free_decode_with_ai(
    payload: FreeDecodeIn,
    classification: Classification,
    message_focus: str | None = None,
    contact_memory_context: str | None = None,
) -> FreeDecodeOutput | None:
    settings = get_settings()
    schema_hint = {
        "dominant_lens": {"fa": "امنیت و اعتماد", "en": "Oxytocin Lens", "key": "oxytocin"},
        "dominant_lens_explanation": "string",
        "why_this_lens": "string",
        "message_focus": "string",
        "personalization_note": "string | null",
        "secondary_lenses": [{"fa": "شأن و احترام", "en": "Serotonin Lens", "key": "serotonin"}],
        "lens_mix": {"dopamine": 20, "oxytocin": 65, "serotonin": 15},
        "tone_stress": {"label": "کنایه‌آمیز", "intensity": 58},
        "likely_underlying_need": "string",
        "conversation_risk": "string",
        "recommended_direction": "string",
        "confidence": "پایین | متوسط | بالا",
        "alternative_read": "string",
        "insight_line": "string",
        "situation_arc": "string | null",
        "privacy_warning": None,
        "cta": "string",
    }
    episode_context = payload.episode_context()
    user_prompt = {
        "task": "free_decode",
        "message_text": payload.message_text,
        "message_focus": message_focus,
        "relationship_type": payload.relationship_type,
        "user_goal": payload.user_goal,
        "optional_context": payload.optional_context,
        "episode_context": episode_context,
        "contact_memory_context": contact_memory_context,
        "rule_engine_analysis": classification_payload(classification),
        "requirements": [
            "پاسخ آماده کامل نده.",
            "حتماً تحلیل را به message_focus و جزئیات خود message_text وصل کن؛ خروجی عمومی و قابل استفاده برای هر پیام ننویس.",
            "اگر contact_memory_context وجود دارد، از آن فقط برای شخصی‌سازی محتاطانه استفاده کن و به عنوان تشخیص قطعی شخصیت مخاطب ننویس.",
            "لنز غالب را توضیح بده و تاکید کن تشخیص هورمونی واقعی نیست.",
            "از قطعیت درباره نیت یا شخصیت طرف مقابل پرهیز کن.",
            "از rule_engine_analysis استفاده کن، اما اگر متن خلافش را نشان می‌دهد، محتاطانه اصلاح کن.",
            "چرا این لنز دیده می‌شود را با اشاره به لحن/کلمه‌های پیام توضیح بده.",
            "insight_line: یک جمله‌ی کوتاه، مشخص و انسانی که نیازِ پنهان را دقیق بگوید (مثلِ «این پیام عصبانی نیست، ترسیده»). کلی و کلیشه‌ای نباشد (مثلِ «احساساتِ پیچیده‌ای دارد» قابل قبول نیست).",
            "situation_arc: فقط اگر episode_context داده شده، یک روایتِ کوتاهِ ساختاری از قوسِ موقعیت بده — کجای ماجرا اعتماد لرزید/حسِ بی‌احترامی آمد/تهدید فعال شد — نه فقط واکنش به پیامِ آخر. اگر episode_context نبود، null بگذار. هیچ ادعای زیستی/پزشکیِ قطعی نزن؛ لنزها فقط زبانِ استعاری‌اند.",
            "فارسی طبیعی بنویس.",
        ],
        "json_schema_shape": schema_hint,
    }
    cache_key = _build_cache_key(user_prompt, _model_for_task("free"))
    if settings.ai_semantic_cache_enabled and not payload.ghost_mode:
        cached = get_cached_response(task="free_decode", cache_key=cache_key)
        if cached:
            cached["lens_mix"] = lens_mix_from_classification(classification).model_dump()
            cached["tone_stress"] = tone_stress_from_classification(classification).model_dump()
            return FreeDecodeOutput.model_validate(cached)
    data = await _chat_json(user_prompt, model=_model_for_task("free"))
    if data is None:
        return None
    data["message_focus"] = data.get("message_focus") or message_focus
    if contact_memory_context and not data.get("personalization_note"):
        data["personalization_note"] = "این تحلیل با پرونده مخاطب و زمینه‌های قبلی همین رابطه تنظیم شده است."
    if has_sensitive_info(payload.message_text) and not data.get("privacy_warning"):
        data["privacy_warning"] = "برای امنیت، بهتر است اطلاعات شخصی مثل شماره، آدرس یا نام کامل را حذف کنی."
    data["lens_mix"] = lens_mix_from_classification(classification).model_dump()
    data["tone_stress"] = tone_stress_from_classification(classification).model_dump()
    if settings.ai_semantic_cache_enabled and not payload.ghost_mode:
        set_cached_response(task="free_decode", cache_key=cache_key, response=data, model_used=_model_for_task("free"))
    try:
        return FreeDecodeOutput.model_validate(data)
    except Exception as exc:
        logger.error("free_decode schema validation failed: %s | keys=%s", exc, list(data.keys()))
        return None


# Above this many characters the episode/context is compressed by the cheap
# free model before being sent to the expensive paid model (roadmap §10 / T10.2).
PAID_CONTEXT_COMPRESS_THRESHOLD = 1200


def _should_compress_context(text: str | None) -> bool:
    return bool(text) and len(text) > PAID_CONTEXT_COMPRESS_THRESHOLD  # type: ignore[arg-type]


async def _compress_context(text: str, message_text: str | None) -> str | None:
    """Cheap-model pass that turns a long episode into a tight structured summary.

    Not a trade-off but a synergy: fewer tokens to the paid model AND a cleaner
    structure for it to work with. Returns None on failure so the caller can
    fall back to the raw (truncated) text.
    """
    payload = {
        "task": "compress_context",
        "message_text": message_text,
        "raw_context": text,
        "requirements": [
            "این زمینه‌ی طولانی را به یک خلاصه‌ی کوتاهِ ساختاریافته تبدیل کن.",
            "فقط حقایقِ مهم برای فهمِ موقعیت را نگه دار؛ حرفِ تکراری و حاشیه را دور بریز.",
            "هیچ تفسیر یا قضاوتی اضافه نکن؛ فقط فشرده کن.",
        ],
        "json_schema_shape": {
            "relationship": "رابطه چطور بوده (کوتاه)",
            "what_happened": "پیشامد / قوسِ ماجرا (کوتاه)",
            "their_behavior": "رفتار طرف مقابل (کوتاه)",
            "recent_points": ["نکته‌های مهمِ پیام‌های اخیر"],
        },
    }
    data = await _chat_json(payload, model=_model_for_task("free"), system_prompt=COMPRESS_SYSTEM_PROMPT)
    if not isinstance(data, dict):
        return None
    parts: list[str] = []
    if data.get("relationship"):
        parts.append(f"رابطه: {data['relationship']}")
    if data.get("what_happened"):
        parts.append(f"پیشامد: {data['what_happened']}")
    if data.get("their_behavior"):
        parts.append(f"رفتار طرف مقابل: {data['their_behavior']}")
    pts = data.get("recent_points")
    if isinstance(pts, list) and pts:
        parts.append("نکته‌های اخیر: " + " | ".join(str(p) for p in pts[:5]))
    return "\n".join(parts) if parts else None


async def _paid_decode_with_ai(
    free_output: FreeDecodeOutput,
    relationship_type: str,
    user_goal: str,
    contact_profile_summary: str | None = None,
    message_text: str | None = None,
    optional_context: str | None = None,
) -> PaidDecodeOutput | None:
    settings = get_settings()
    # Compress an over-long context with the cheap model before paid generation.
    if _should_compress_context(optional_context):
        compressed = await _compress_context(optional_context, message_text)  # type: ignore[arg-type]
        if compressed:
            optional_context = compressed
    schema_hint = {
        "deep_read": "string",
        "dominant_lens": free_output.dominant_lens.model_dump(),
        "secondary_lenses": [lens.model_dump() for lens in free_output.secondary_lenses],
        "personalization_note": "string | null",
        "reply_options": [
            {"label": "نرم", "text": "string", "why_it_works": "string",
             "reaction_prediction": "string",
             "reaction_forecast": {"likely_reaction": "string", "reason": "string", "risk_level": "کم | متوسط | زیاد"}},
            {"label": "تعیین‌کننده مرز روابط", "text": "string", "why_it_works": "string",
             "reaction_prediction": "string",
             "reaction_forecast": {"likely_reaction": "string", "reason": "string", "risk_level": "کم | متوسط | زیاد"}},
            {"label": "کوتاه", "text": "string", "why_it_works": "string",
             "reaction_prediction": "string",
             "reaction_forecast": {"likely_reaction": "string", "reason": "string", "risk_level": "کم | متوسط | زیاد"}},
            {"label": "قاطع و آرام", "text": "string", "why_it_works": "string",
             "reaction_prediction": "string",
             "reaction_forecast": {"likely_reaction": "string", "reason": "string", "risk_level": "کم | متوسط | زیاد"}},
            {"label": "هدف‌محور", "text": "string", "why_it_works": "string",
             "reaction_prediction": "string",
             "reaction_forecast": {"likely_reaction": "string", "reason": "string", "risk_level": "کم | متوسط | زیاد"}},
        ],
        "words_to_avoid": ["string"],
        "safe_opening_line": "string",
        "copy_ready_reply": "string",
        "attribution_reply": "string",
        "follow_up_question": "string",
    }
    # Golden examples can be delivered either as real few-shot conversation
    # turns (preferred — models imitate tone better from genuine turns) or as a
    # list inside the payload (fallback). The turns are NOT part of user_prompt,
    # so the cache key stays stable (the same relationship/goal yields the same
    # turns deterministically).
    use_fewshot_turns = settings.ai_paid_fewshot_turns_enabled
    few_shot_messages = (
        golden_examples_as_messages(relationship_type, user_goal, limit=4) if use_fewshot_turns else None
    )
    user_prompt = {
        "task": "paid_decode",
        "message_text": message_text,
        "message_focus": free_output.message_focus,
        "optional_context": optional_context,
        "free_output": free_output.model_dump(),
        "relationship_type": relationship_type,
        "user_goal": user_goal,
        "contact_profile_summary": contact_profile_summary,
        "reply_playbook": paid_reply_playbook(relationship_type, user_goal, free_output.dominant_lens.key),
        "requirements": [
            "مرزِ سالم در همهٔ پاسخ‌ها: هیچ پاسخی التماس‌وار یا عذرخواهانه نباشد. حتی پاسخ «نرم» هم موضعِ کاربر را نگه می‌دارد — گرما می‌دهد بدون اینکه موضع را تسلیم کند. پاسخ‌های «تعیین‌کننده مرز» باید خطِ قرمز را مستقیم بگویند بدون «ببخشید»، «می‌دونم سختِ» یا توجیه اضافه.",
            "دقتِ احساسی: لحنِ پیامِ ورودی را با دقت تشخیص بده — تند/سرد/کنایه/قربانی‌گونه/کنترل‌گر؟ پاسخ باید همان سطح احساسی را ببیند و نامش را بداند، نه سطحی‌تر و نه بیشتر.",
            "از نمونه‌هایِ سبکِ تأییدشده (چه گفتگوهای نمونه‌ی قبلی، چه «نمونه‌های_طلایی» اگر داده شده) لحن و ساختار را تقلید کن: شکسته، کوتاه، سه‌جمله‌ای، بدونِ بهانه و دفاع (مثلِ «سرم شلوغ بود» ننویس). نمونه‌ها را عیناً کپی نکن؛ فقط جنسِ لحن و ساختارشان را بگیر و برای همین پیام بساز.",
            "۴ تا ۵ پاسخ آماده و قابل کپی بده؛ پاسخ‌ها واقعاً از نظر زاویه و کاربرد متفاوت باشند — هرکدام یک موضع/لحنِ متمایز، نه بازنویسیِ یک جمله.",
            "هر پاسخ باید به message_focus یا جزئیات message_text مربوط باشد. جواب‌هایی مثل «می‌فهمم چرا اینطوری برداشت کردی» بدون اشاره به موضوع مشخص پیام کافی نیست.",
            "اگر contact_profile_summary وجود دارد، پاسخ را با حافظه همین مخاطب شخصی‌سازی کن اما از برچسب قطعی شخصیتی پرهیز کن.",
            "حتماً این labelها را پوشش بده مگر اینکه context خلافش باشد: نرم، تعیین‌کننده مرز روابط، کوتاه، قاطع و آرام، هدف‌محور.",
            "برای کار لحن حرفه‌ای، برای رابطه لحن انسانی و بدون التماس، برای اکس محترمانه و تعیین‌کننده مرز روابط باشد.",
            "copy_ready_reply را از بهترین ترکیب برای user_goal بساز، نه الزاماً اولین پاسخ.",
            "کلمات ممنوع و دلیل هر پاسخ را بده.",
            "برای هر reply_options یک reaction_prediction کوتاه بده که واکنش احتمالی طرف مقابل را بدون قطعیت‌نمایی توضیح دهد.",
            "همچنین برای هر reply_options یک reaction_forecast ساختاریافته بده: likely_reaction (واکنشِ محتمل مثل «آرام می‌شود» یا «اول جبهه می‌گیرد»)، reason (دلیلِ کوتاه)، و risk_level یکی از «کم/متوسط/زیاد». لحن محتاط باشد («احتمالاً»)، نه قطعی، چون پیش‌بینیِ غلط اعتماد را می‌ریزد.",
            "اگر contact_profile_summary وجود دارد، reaction_forecast را با تاریخچه‌ی همین مخاطب تعدیل کن (مثلاً اگر قبلاً لحنِ محکم سردش کرده، ریسکِ گزینه‌های محکم را بالاتر بزن و در reason به الگوی همین رابطه اشاره کن) — اما هیچ برچسبِ قطعیِ شخصیتی نزن.",
            "نسخه با استناد به Message Decoder اختیاری و نرم باشد.",
            "هیچ پاسخ manipulative، guilt-trip، تحقیرآمیز یا تحریک‌کننده تولید نکن.",
            "فارسی طبیعی بنویس، نه رباتی یا بیش از حد روانشناسانه.",
        ],
        "json_schema_shape": schema_hint,
    }
    if not use_fewshot_turns:
        user_prompt["نمونه‌های_طلایی"] = golden_examples_for_prompt(relationship_type, user_goal, limit=4)
    cache_key = _build_cache_key(user_prompt, _model_for_task("paid"))
    if settings.ai_semantic_cache_enabled:
        cached = get_cached_response(task="paid_decode", cache_key=cache_key)
        if cached:
            return PaidDecodeOutput.model_validate(cached)
    data = await _chat_json(user_prompt, model=_model_for_task("paid"), few_shot_messages=few_shot_messages)
    if data is None:
        return None
    if free_output.message_focus and not data.get("personalization_note"):
        data["personalization_note"] = _paid_personalization_note(free_output.message_focus, contact_profile_summary)

    # Generate → critique → revise: one self-critique pass that also consumes the
    # deterministic forbidden-phrase inspector (model words_to_avoid + defensive
    # excuses + clinical jargon). Runs once for paid only.
    #
    # The full quality critique is gated by AI_PAID_SELF_CRITIQUE_ENABLED so paid
    # latency can be halved when needed. Forbidden phrases are ALWAYS scrubbed,
    # regardless of the flag, so the safety/quality floor never depends on it.
    forbidden = find_forbidden_phrases(_paid_reply_texts(data), data.get("words_to_avoid") or [])
    if settings.ai_paid_self_critique_enabled or forbidden:
        data = await _self_critique_paid(data, forbidden, relationship_type, user_goal)
        # Hard backstop: if an unambiguous forbidden phrase still slipped through
        # the revise, try one more focused pass before giving up.
        still = find_forbidden_phrases(_paid_reply_texts(data), data.get("words_to_avoid") or [])
        if still:
            data = await _self_critique_paid(data, still, relationship_type, user_goal)

    if settings.ai_semantic_cache_enabled:
        set_cached_response(task="paid_decode", cache_key=cache_key, response=data, model_used=_model_for_task("paid"))
    try:
        return PaidDecodeOutput.model_validate(data)
    except Exception as exc:
        logger.error("paid_decode schema validation failed: %s | keys=%s", exc, list(data.keys()))
        return None


# The self-critique checklist applied to every paid output before it is shown.
SELF_CRITIQUE_CHECKLIST = [
    "آیا پاسخ دفاعی است یا بهانه می‌آورد؟ (مثلِ «سرم شلوغ بود»، «درگیر کاری بودم») — بهانه را حذف کن و به‌جایش حسِ طرف را تأیید کن.",
    "آیا پاسخ کلی و مبهم است؟ اگر می‌شود جزئی‌ترش کن (یک اقدام یا زمانِ مشخص بهتر از وعده‌ی کلی است).",
    "اگر طرف مقابل قدمِ نرم برداشته یا عذرخواهی کرده، آیا پاسخ آن را با گرمی گرفته یا خنثی‌اش کرده؟ قدمِ نرم را بگیر.",
    "آیا واژه‌ی روان‌شناسی یا کلیشه‌ی درمانی در متنِ پاسخ هست؟ حذفش کن.",
    "آیا پاسخ از مرز اخلاقی عبور می‌کند (فریب، گناه‌اندازی، وادارکردن)؟ به یک پاسخ صادقانه و سالم تبدیلش کن.",
]


async def _self_critique_paid(
    data: dict[str, Any],
    forbidden_phrases: list[str],
    relationship_type: str,
    user_goal: str,
) -> dict[str, Any]:
    """One corrective self-critique pass over a paid output (generate→critique→revise).

    Always runs for the paid path. The model reviews each reply against
    SELF_CRITIQUE_CHECKLIST plus any forbidden phrases the deterministic
    inspector found, and returns an improved version of the SAME JSON — leaving
    replies that already pass untouched. Falls back to the original data if the
    call fails or the result does not validate, so it can only improve, never
    break, the response. paid only (not free) to bound latency/cost.
    """
    revise_payload = {
        # task must be "paid_decode" so _chat_json routes to the paid endpoint/model.
        "task": "paid_decode",
        "subtask": "self_critique_revise",
        "relationship_type": relationship_type,
        "user_goal": user_goal,
        "current_output": data,
        "checklist": SELF_CRITIQUE_CHECKLIST,
        "forbidden_phrases_must_remove": forbidden_phrases,
        "requirements": [
            "هر پاسخ را در برابر checklist بررسی کن و فقط جایی را اصلاح کن که از یکی از موارد چک‌لیست رد می‌شود.",
            "هیچ‌کدام از forbidden_phrases_must_remove نباید در متنِ هیچ پاسخی بماند؛ یا حذفش کن یا با تأییدِ حسِ طرف جایگزینش کن.",
            "پاسخ‌هایی که از قبل خوب‌اند را دست‌نخورده نگه دار؛ بازنویسیِ بی‌دلیل نکن.",
            "لحن، ساختار، تعداد پاسخ‌ها و کلیدهای JSON را دقیقاً مثلِ خروجیِ فعلی نگه دار؛ همان schema را برگردان.",
            "پاسخ‌ها شکسته، کوتاه، سه‌جمله‌ای، طبیعی و قابل ارسال بمانند.",
        ],
        "json_schema_shape": {k: data.get(k) for k in data},
    }
    revised = await _chat_json(revise_payload, model=_model_for_task("paid"))
    if not isinstance(revised, dict):
        return data
    try:
        PaidDecodeOutput.model_validate(revised)
    except Exception:
        return data
    return revised


async def _chat_json(
    user_payload: dict[str, Any],
    model: str | None = None,
    system_prompt: str | None = None,
    few_shot_messages: list[dict[str, str]] | None = None,
) -> dict[str, Any] | None:
    settings = get_settings()
    task = str(user_payload.get("task") or "free_decode")
    is_paid = task == "paid_decode"
    endpoint_base = settings.ai_paid_api_base_url if is_paid else settings.ai_api_base_url
    api_key = settings.ai_paid_api_key if is_paid else settings.ai_api_key
    temperature = settings.ai_paid_temperature if is_paid else settings.ai_free_temperature
    max_tokens = settings.ai_paid_max_tokens if is_paid else settings.ai_free_max_tokens
    endpoint = endpoint_base.rstrip("/") + "/chat/completions"
    messages: list[dict[str, str]] = [{"role": "system", "content": system_prompt or SYSTEM_PROMPT}]
    if few_shot_messages:
        messages.extend(few_shot_messages)
    messages.append({"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)})
    body = {
        "model": model or settings.ai_model,
        "messages": messages,
        "temperature": temperature,
        "max_tokens": max_tokens,
        "response_format": {"type": "json_object"},
    }
    # Token-repetition penalty is off by default (see config) because it also
    # penalises structural JSON tokens. Only sent when explicitly enabled.
    if settings.ai_frequency_penalty:
        body["frequency_penalty"] = settings.ai_frequency_penalty
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    last_exc: Exception | None = None
    for attempt, delay in enumerate((*_AI_RETRY_DELAYS, None)):
        try:
            async with httpx.AsyncClient(timeout=90) as client:
                response = await client.post(endpoint, headers=headers, json=body)
                response.raise_for_status()
                content = response.json()["choices"][0]["message"]["content"]
                return _parse_json_object(content)
        except Exception as exc:
            last_exc = exc
            status = exc.response.status_code if isinstance(exc, httpx.HTTPStatusError) else None
            # Don't retry client errors (4xx) — they won't fix themselves.
            if status is not None and 400 <= status < 500:
                logger.error("AI API client error %s: %s", status, exc.response.text[:200])
                return None
            logger.warning(
                "AI API error (attempt %d/%d): %s — %s",
                attempt + 1, len(_AI_RETRY_DELAYS) + 1,
                type(exc).__name__, str(exc)[:200],
            )
            if delay is not None:
                await asyncio.sleep(delay)
    logger.error("AI API failed after %d attempts: %s", len(_AI_RETRY_DELAYS) + 1, last_exc)
    return None


def _build_cache_key(user_prompt: dict[str, Any], model: str) -> str:
    """Cache key that is sensitive to the prompt version and the model used.

    Without this, changing SYSTEM_PROMPT / PROMPT_VERSION or swapping the model
    would keep serving stale cached responses, making any prompt tuning
    impossible to observe. Bumping PROMPT_VERSION now busts the whole cache.
    """
    keyed = {
        "prompt_version": PROMPT_VERSION,
        "model": model,
        "payload": user_prompt,
    }
    return hashlib.sha256(json.dumps(keyed, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


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


def _with_focus(text: str, message_focus: str | None) -> str:
    if not message_focus or message_focus in text:
        return text
    return f"در زمینه {message_focus}، {text}"


def _personalize_replies_for_focus(
    replies: list[ReplyOption],
    message_focus: str,
    professional: bool,
) -> list[ReplyOption]:
    return [
        reply.model_copy(update={"text": _append_focus(reply.text, message_focus)})
        for reply in replies
    ]


def _append_focus(text: str, message_focus: str) -> str:
    if message_focus in text:
        return text
    return f"در مورد {message_focus}، {text}"


def _paid_personalization_note(message_focus: str | None, contact_profile_summary: str | None) -> str | None:
    parts: list[str] = []
    if message_focus:
        parts.append(f"پاسخ‌ها برای همین موضوع تنظیم شده‌اند: {message_focus}.")
    if contact_profile_summary:
        parts.append("حافظه این مخاطب هم در انتخاب لحن و مرزبندی لحاظ شده است.")
    return " ".join(parts) if parts else None
