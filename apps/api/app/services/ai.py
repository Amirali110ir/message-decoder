from __future__ import annotations

import hashlib
import json
import re
from typing import Any

import httpx

from app.config import get_settings
from app.schemas import FreeDecodeIn, FreeDecodeOutput, LensLabel, LensMix, PaidDecodeOutput, ReplyOption, SafetyOutput, ToneStress
from app.services.cache import get_cached_response, set_cached_response
from app.services.rule_engine import (
    RULE_ENGINE_VERSION,
    Classification,
    classification_payload,
    classify,
    paid_reply_playbook,
)
from app.utils import has_sensitive_info


PROMPT_VERSION = "message-decoder-system-v0.3"
MODEL_VERSION = "mock-v0.1"
OUTPUT_SCHEMA_VERSION = "decode-schema-v0.2"


class PaidDecodeUnavailable(Exception):
    pass


SYSTEM_PROMPT = """
تو Message Decoder by NeuroLens هستی.

تو یک ابزار فارسی‌زبان برای رمزگشایی پیام‌ها، چت‌ها و ایمیل‌های مبهم، سرد، تند، احساسی، کنایه‌آمیز یا حرفه‌ای هستی.

وعده محصول: قبل از جواب دادن، بفهم پشت پیامش چیست و جواب کم‌ریسک‌تر بگیر.

هدف اصلی تو کمک به کاربر برای فهمیدن نیاز، ترس، فشار، سوءتفاهم، حساسیت یا ریسک پنهان پشت پیام طرف مقابل است. هدف دوم ساختن پاسخ بهتر، کم‌ریسک‌تر، انسانی‌تر، تعیین‌کننده‌تر مرز روابط یا حرفه‌ای‌تر است.

محدودیت‌های مهم:
- از روی متن، سطح واقعی هورمون تشخیص نده.
- تشخیص روانشناختی، پزشکی یا شخصیتی نده.
- برچسب‌هایی مثل narcissist، toxic، bipolar، اختلال شخصیت، افسرده، وابسته یا کنترل‌گر را به عنوان حکم قطعی استفاده نکن.
- درباره نیت طرف مقابل قطعی حرف نزن.
- از عبارت‌هایی مثل «احتمالاً»، «ممکن است»، «نشانه‌هایی از»، «برداشت محتاطانه» استفاده کن.
- سه هورمون را فقط به عنوان لنز رفتاری توضیح بده، نه واقعیت آزمایشگاهی.

سه لنز اصلی:
۱. لنز هدف و کنترل — Dopamine Lens: هدف، نتیجه، کنترل، عجله، ناکامی، فشار برای اقدام. سؤال پنهان: «چرا چیزی که می‌خواهم جلو نمی‌رود؟»
۲. لنز امنیت و اعتماد — Oxytocin Lens: امنیت عاطفی، اعتماد، نزدیکی، وفاداری، دیده‌شدن، ترس از بی‌اهمیت شدن. سؤال پنهان: «آیا هنوز برای تو مهمم و می‌توانم به تو اعتماد کنم؟»
۳. لنز شأن و احترام — Serotonin Lens: شأن، احترام، جایگاه، اعتبار، تحقیر، مقایسه، قضاوت. سؤال پنهان: «آیا من دیده شدم، محترم شمرده شدم و جایگاهم حفظ شد؟»

فرآیند تحلیل:
۱. اول خطر را بررسی کن. اگر تهدید، خشونت، خودآسیب‌رسانی، اخاذی، stalking، اجبار، تهدید جنسی، تهدید فیزیکی یا خطر جدی بود، Safety Mode فعال است: پاسخ عاشقانه یا استراتژیک عادی تولید نکن.
۲. لحن پیام را تشخیص بده: سرد، تند، کنایه‌آمیز، passive-aggressive، رسمی، تهدیدکننده، ناراحت، قربانی‌گونه، کنترل‌گر، مبهم، دفاعی، شرمنده‌کننده یا تعیین‌کننده مرز روابط.
۳. لنز غالب و فرعی را انتخاب کن.
۴. نیاز پنهان احتمالی، ریسک پاسخ اشتباه، جهت پاسخ بهتر، احتمال خطا و برداشت جایگزین را توضیح بده.
۵. اگر paid است، پاسخ‌ها باید واقعاً متنوع باشند: نرم، تعیین‌کننده مرز روابط، کوتاه، هدف‌محور، و اگر context کاری/اکس/پایان مکالمه بود نسخه مخصوص همان موقعیت.
۶. اگر کاربر درخواست manipulative داد، درخواست را به پاسخ سالم، قاطع، بالغ و استراتژیک تبدیل کن.

لحن پاسخ‌ها:
- رابطه عاطفی: انسانی، گرم، واضح، بدون التماس.
- اکس: محترمانه، تعیین‌کننده مرز روابط، بدون باز کردن بی‌دلیل رابطه.
- کار و همکار: حرفه‌ای، کوتاه، مسئولیت‌پذیر، بدون دفاع اضافه.
- خانواده: محترمانه، احساسی اما تعیین‌کننده مرز روابط.
- دوست: صمیمی، روشن، بدون حمله.

پاسخ‌ها باید فارسی طبیعی، قابل ارسال، غیررباتی و JSON معتبر مطابق schema خواسته‌شده باشند.
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


def with_reaction_predictions(replies: list[ReplyOption], relationship_type: str, dominant_lens: str) -> list[ReplyOption]:
    fallback = {
        "dopamine": "احتمالاً طرف مقابل سریع‌تر روی اقدام، تصمیم یا پاسخ مشخص تمرکز می‌کند.",
        "oxytocin": "احتمالاً اول دنبال نشانه اطمینان و دیده‌شدن می‌گردد و بعد آرام‌تر توضیح می‌دهد.",
        "serotonin": "احتمالاً به احترام و لحن سنجیده حساس است و اگر شأنش حفظ شود کمتر دفاعی می‌شود.",
    }.get(dominant_lens, "احتمالاً واکنش اولیه به لحن شما وابسته است؛ کوتاه و روشن نگه داشتن پاسخ ریسک را کم می‌کند.")
    if relationship_type in ("manager_colleague", "customer"):
        fallback = "احتمالاً پاسخ حرفه‌ای و زمان‌بندی روشن را بهتر می‌پذیرد و بحث از حالت احساسی خارج می‌شود."
    return [
        reply.model_copy(update={"reaction_prediction": reply.reaction_prediction or fallback})
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
        "privacy_warning": None,
        "cta": "string",
    }
    user_prompt = {
        "task": "free_decode",
        "message_text": payload.message_text,
        "message_focus": message_focus,
        "relationship_type": payload.relationship_type,
        "user_goal": payload.user_goal,
        "optional_context": payload.optional_context,
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
            "فارسی طبیعی بنویس.",
        ],
        "json_schema_shape": schema_hint,
    }
    cache_key = hashlib.sha256(json.dumps(user_prompt, sort_keys=True).encode()).hexdigest()
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
    except Exception:
        return None


async def _paid_decode_with_ai(
    free_output: FreeDecodeOutput,
    relationship_type: str,
    user_goal: str,
    contact_profile_summary: str | None = None,
    message_text: str | None = None,
    optional_context: str | None = None,
) -> PaidDecodeOutput | None:
    settings = get_settings()
    schema_hint = {
        "deep_read": "string",
        "dominant_lens": free_output.dominant_lens.model_dump(),
        "secondary_lenses": [lens.model_dump() for lens in free_output.secondary_lenses],
        "personalization_note": "string | null",
        "reply_options": [
            {"label": "نرم", "text": "string", "why_it_works": "string", "reaction_prediction": "string"},
            {"label": "تعیین‌کننده مرز روابط", "text": "string", "why_it_works": "string", "reaction_prediction": "string"},
            {"label": "کوتاه", "text": "string", "why_it_works": "string", "reaction_prediction": "string"},
            {"label": "قاطع و آرام", "text": "string", "why_it_works": "string", "reaction_prediction": "string"},
            {"label": "هدف‌محور", "text": "string", "why_it_works": "string", "reaction_prediction": "string"},
        ],
        "words_to_avoid": ["string"],
        "safe_opening_line": "string",
        "copy_ready_reply": "string",
        "attribution_reply": "string",
        "follow_up_question": "string",
    }
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
            "۴ تا ۵ پاسخ آماده و قابل کپی بده؛ پاسخ‌ها واقعاً از نظر زاویه و کاربرد متفاوت باشند.",
            "هر پاسخ باید به message_focus یا جزئیات message_text مربوط باشد. جواب‌هایی مثل «می‌فهمم چرا اینطوری برداشت کردی» بدون اشاره به موضوع مشخص پیام کافی نیست.",
            "اگر contact_profile_summary وجود دارد، پاسخ را با حافظه همین مخاطب شخصی‌سازی کن اما از برچسب قطعی شخصیتی پرهیز کن.",
            "حتماً این labelها را پوشش بده مگر اینکه context خلافش باشد: نرم، تعیین‌کننده مرز روابط، کوتاه، قاطع و آرام، هدف‌محور.",
            "برای کار لحن حرفه‌ای، برای رابطه لحن انسانی و بدون التماس، برای اکس محترمانه و تعیین‌کننده مرز روابط باشد.",
            "copy_ready_reply را از بهترین ترکیب برای user_goal بساز، نه الزاماً اولین پاسخ.",
            "کلمات ممنوع و دلیل هر پاسخ را بده.",
            "برای هر reply_options یک reaction_prediction کوتاه بده که واکنش احتمالی طرف مقابل را بدون قطعیت‌نمایی توضیح دهد.",
            "نسخه با استناد به Message Decoder اختیاری و نرم باشد.",
            "هیچ پاسخ manipulative، guilt-trip، تحقیرآمیز یا تحریک‌کننده تولید نکن.",
            "فارسی طبیعی بنویس، نه رباتی یا بیش از حد روانشناسانه.",
        ],
        "json_schema_shape": schema_hint,
    }
    cache_key = hashlib.sha256(json.dumps(user_prompt, sort_keys=True).encode()).hexdigest()
    if settings.ai_semantic_cache_enabled:
        cached = get_cached_response(task="paid_decode", cache_key=cache_key)
        if cached:
            return PaidDecodeOutput.model_validate(cached)
    data = await _chat_json(user_prompt, model=_model_for_task("paid"))
    if data is None:
        return None
    if free_output.message_focus and not data.get("personalization_note"):
        data["personalization_note"] = _paid_personalization_note(free_output.message_focus, contact_profile_summary)
    if settings.ai_semantic_cache_enabled:
        set_cached_response(task="paid_decode", cache_key=cache_key, response=data, model_used=_model_for_task("paid"))
    try:
        return PaidDecodeOutput.model_validate(data)
    except Exception:
        return None


async def _chat_json(user_payload: dict[str, Any], model: str | None = None) -> dict[str, Any] | None:
    settings = get_settings()
    task = str(user_payload.get("task") or "free_decode")
    is_paid = task == "paid_decode"
    endpoint_base = settings.ai_paid_api_base_url if is_paid else settings.ai_api_base_url
    api_key = settings.ai_paid_api_key if is_paid else settings.ai_api_key
    temperature = settings.ai_paid_temperature if is_paid else settings.ai_free_temperature
    endpoint = endpoint_base.rstrip("/") + "/chat/completions"
    body = {
        "model": model or settings.ai_model,
        "messages": [
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": json.dumps(user_payload, ensure_ascii=False)},
        ],
        "temperature": temperature,
        "response_format": {"type": "json_object"},
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    try:
        async with httpx.AsyncClient(timeout=90) as client:
            response = await client.post(endpoint, headers=headers, json=body)
            response.raise_for_status()
            content = response.json()["choices"][0]["message"]["content"]
            return _parse_json_object(content)
    except Exception as e:
        print(f"AI API Error: {type(e).__name__} - {str(e)}")
        if isinstance(e, httpx.HTTPStatusError):
            print(f"HTTP Status Error: {e.response.status_code} - {e.response.text}")
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


def _with_focus(text: str, message_focus: str | None) -> str:
    if not message_focus or message_focus in text:
        return text
    return f"در زمینه {message_focus}، {text}"


def _personalize_replies_for_focus(
    replies: list[ReplyOption],
    message_focus: str,
    professional: bool,
) -> list[ReplyOption]:
    if "داروخانه" in message_focus:
        if professional:
            replacements = {
                "حرفه‌ای": "پیام شما را درباره تصمیم داروخانه و نگرانی‌هایش گرفتم. حق دارید شفافیت بخواهید؛ تا امروز وضعیت هزینه‌ها، مجوزها و قدم بعدی را جمع‌بندی می‌کنم و بدون دفاع اضافه با شما چک می‌کنم.",
                "کوتاه": "در مورد داروخانه حق دارید شفافیت بخواهید. امروز وضعیت دقیق و قدم بعدی را جمع‌بندی می‌کنم.",
                "قاطع و آرام": "قبول دارم تصمیم داروخانه نیاز به بررسی دقیق‌تر دارد. بدون توجیه، عددها و ریسک‌ها را دوباره می‌چینم و بعد تصمیم بعدی را روشن می‌کنم.",
            }
        else:
            replacements = {
                "نرم": "می‌فهمم چرا تصمیم داروخانه ذهنت را درگیر کرده. من هم نمی‌خواهم از روی ترس یا غرور جلو بروم؛ بیا واقع‌بینانه هزینه‌ها، مجوزها و قدم بعدی را دوباره بررسی کنیم.",
                "تعیین‌کننده مرز روابط": "نگرانی‌ات درباره داروخانه را می‌شنوم، ولی دوست ندارم این موضوع به سرزنش کلی من تبدیل شود. اگر درباره خود تصمیم حرف بزنیم، بهتر می‌توانم مسئولانه بررسی‌اش کنم.",
                "کوتاه": "در مورد داروخانه نگرانی‌ات را فهمیدم. می‌خواهم با عدد و واقعیت دوباره بررسی‌اش کنم، نه با دفاع یا ترس.",
                "قاطع و آرام": "ممکن است در تصمیم داروخانه اشتباه کرده باشم، اما می‌خواهم آرام و دقیق اصلاحش کنم. بیایید به جای مقصر پیدا کردن، قدم بعدی را روشن کنیم.",
            }
        return [
            reply.model_copy(update={"text": replacements.get(reply.label, _append_focus(reply.text, message_focus))})
            for reply in replies
        ]

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
