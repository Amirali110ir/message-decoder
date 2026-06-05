"""Golden few-shot examples for the romantic conflict / avoid-needy wedge.

Each example is a hand-approved pair of (incoming message -> ideal reply) that
embodies the form + content rules of the v0.4 system prompt:

  Form    : shekaste (colloquial), short (1-3 chat-sized sentences), direct,
            "تو" address, no psychology jargon.
  Content : settle the feeling before logic; validate the feeling, not the
            claim; be specific, not general; NO defensive excuse (never
            "سرم شلوغ بود" / "درگیر کاری بودم"); catch the other person's soft
            step; leave an open door, not a demand.
  Structure: sentence 1 disarms the threat, sentence 2 states your position
            without defending, sentence 3 leaves a door open.

These are injected into the paid prompt as few-shot exemplars (see
``select_golden_examples``). They are deliberately scoped to the wedge:
relationship_type == "romantic" and user_goal in {"calm_conflict",
"avoid_needy"}.

Golden rule honoured by every reply here: help the user be more honest and
clear, never to manipulate or guilt-trip the other person.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenExample:
    id: str
    situation: str          # short tag describing the incoming-message type
    user_goal: str          # "calm_conflict" | "avoid_needy"
    incoming: str           # the message the user received
    reply: str              # the ideal, copy-ready reply
    why: str                # why this reply is good (not sent to the model verbatim)


WEDGE_RELATIONSHIP = "romantic"

# 20 hand-approved examples. Order is not significant; selection is by goal.
GOLDEN_EXAMPLES: list[GoldenExample] = [
    GoldenExample(
        id="cold_dismissal",
        situation="کناره‌گیریِ سرد و قهرآلود",
        user_goal="calm_conflict",
        incoming="باشه دیگه. معلومه که سرت شلوغه. منم دیگه مزاحم نمیشم.",
        reply="مزاحم چیه آخه. الان حواسم کاملاً بهته. بگو چی شد که این حسو پیدا کردی.",
        why="تهدید را خاموش می‌کند («مزاحم چیه») بدون بهانه‌آوردن برای دیرکرد؛ موضع گرم را مشخص می‌گوید؛ در باز می‌گذارد بدون بازجویی.",
    ),
    GoldenExample(
        id="late_reply_complaint",
        situation="گله از دیر جواب دادن",
        user_goal="calm_conflict",
        incoming="چرا انقدر دیر جواب میدی؟ انگار اصلا برات مهم نیست.",
        reply="می‌فهمم چرا این حسو داری و دوست ندارم اینطوری فکر کنی. تو برام مهمی، خیلی هم مهمی. بیا یه قرار بذاریم سرفرصت حرف بزنیم.",
        why="حس را می‌بیند بدون اینکه «حق با توئه» بگوید؛ موضع را مستقیم و بدون بهانه‌ی دیرکرد می‌گوید؛ یک قدم مشخص پیشنهاد می‌دهد.",
    ),
    GoldenExample(
        id="vague_nevermind",
        situation="پیامِ مبهم و سربسته",
        user_goal="calm_conflict",
        incoming="هیچی. ولش کن. مهم نیست.",
        reply="حس می‌کنم یه چیزی هست که اذیتت کرده. برام مهمه بدونم، جدی میگم. هر وقت آماده بودی بگو، عجله‌ای نیست.",
        why="پشتِ «ولش کن» را می‌بیند؛ اهمیت‌دادن را مشخص می‌گوید؛ بدون فشار در را باز می‌گذارد.",
    ),
    GoldenExample(
        id="sarcasm",
        situation="کنایه و طعنه",
        user_goal="calm_conflict",
        incoming="نه بابا، تو که همیشه سرت شلوغه. ما کجا و وقتِ تو کجا.",
        reply="انگار حسابی دلت پره ازم. کنایه نزنیم بهتره، چون دوست دارم واقعاً بفهمم چی شده. بگو کجا کم گذاشتم؟",
        why="طعنه را آرام به رسمیت می‌شناسد بدون اینکه جبهه بگیرد؛ مرزِ نرمِ «کنایه نزنیم» می‌گذارد؛ مستقیم دعوت به اصل ماجرا می‌کند.",
    ),
    GoldenExample(
        id="jealousy",
        situation="حسادت و سوال‌پیچ",
        user_goal="calm_conflict",
        incoming="با کی بودی که جواب نمیدادی؟ چرا آنلاین بودی ولی جواب من رو ندادی؟",
        reply="می‌بینم که نگران شدی و این حسو دوست ندارم بینمون باشه. چیزی نبوده که بخوام ازت پنهون کنم. بیا حرف بزنیم تا این نگرانی بمونه تو دلت.",
        why="نگرانی را می‌بیند نه اتهام را؛ شفافیت را بدون حالتِ تدافعی می‌گوید؛ به‌جای پاسخِ بازجویی، گفتگو پیشنهاد می‌کند.",
    ),
    GoldenExample(
        id="long_silence_then_ping",
        situation="سکوتِ طولانی و بعد یک پیامِ کوتاه",
        user_goal="calm_conflict",
        incoming="زنده‌ای؟",
        reply="آره هستم، ببخش که این چند وقت کم پیدا بودم. دلم برات تنگ شده بود راستش. چطوری تو؟",
        why="بدون توجیهِ طولانی، کوتاه عذرِ غیبت را می‌گیرد (نه بهانه)؛ گرمی نشان می‌دهد؛ در را برای ادامه باز می‌کند.",
    ),
    GoldenExample(
        id="their_half_apology",
        situation="عذرخواهیِ نیمه از طرف مقابل",
        user_goal="calm_conflict",
        incoming="ببخشید اگه دیشب تند رفتم. نمیدونم چرا یهو عصبی شدم.",
        reply="مرسی که گفتی، واقعاً برام ارزش داره. منم دیشب می‌تونستم آروم‌تر باشم. مهم اینه که الان خوبیم.",
        why="قدمِ نرمِ طرف را با گرمی می‌گیرد و خنثی نمی‌کند؛ سهمِ کوچک خودش را بدون خودزنی می‌پذیرد؛ رو به جلو می‌بندد.",
    ),
    GoldenExample(
        id="guilt_trip",
        situation="گناه‌اندازی",
        user_goal="calm_conflict",
        incoming="من هرکاری میکنم بازم برات کمه. انگار هیچ‌وقت کافی نیستم.",
        reply="اصلاً دوست ندارم همچین حسی داشته باشی، چون برام کم نیستی. شاید من خوب نشون ندادم چقدر برام مهمی. بگو چی باعث شده این حسو پیدا کنی؟",
        why="حسِ «کافی نبودن» را آرام می‌کند بدون اینکه وارد بازیِ گناه شود؛ سهمِ خودش را در نشان‌ندادن می‌پذیرد؛ سوالِ باز می‌پرسد.",
    ),
    GoldenExample(
        id="withdrawal",
        situation="بی‌حسی و فاصله‌گرفتن",
        user_goal="calm_conflict",
        incoming="دیگه حسش نیست. خسته شدم از این رابطه.",
        reply="این حرفت برام سنگینه، ولی می‌خوام بفهممش نه اینکه ازش فرار کنم. حس می‌کنم خیلی خسته‌ای. می‌تونیم آروم درباره‌ش حرف بزنیم؟",
        why="سنگینیِ پیام را به رسمیت می‌شناسد بدون وحشت‌زدگی یا التماس؛ خستگیِ طرف را می‌بیند؛ گفتگوی آرام پیشنهاد می‌کند.",
    ),
    GoldenExample(
        id="accusation_selfish",
        situation="اتهامِ خودخواهی",
        user_goal="calm_conflict",
        incoming="تو اصلا به فکر من نیستی. فقط به خودت فکر میکنی.",
        reply="می‌فهمم که الان این حسو داری و برام مهمه. من اینطوری نمی‌بینمت، ولی شاید جایی کم گذاشتم که این حس بهت دست داده. کجا بود که حس کردی به فکرت نیستم؟",
        why="حس را می‌بیند بدون تأییدِ اتهام؛ موضع را روشن می‌گوید و فضای پذیرشِ سهم می‌گذارد؛ مشخص می‌پرسد، نه کلی.",
    ),
    GoldenExample(
        id="pressure_define",
        situation="فشار برای روشن‌کردنِ تکلیف",
        user_goal="calm_conflict",
        incoming="بالاخره تکلیف منو روشن کن. نمیتونم همینطوری بلاتکلیف بمونم.",
        reply="حق داری بخوای بدونی کجای کاریم، این بلاتکلیفی سخته. منم می‌خوام روشن حرف بزنیم نه نصفه. کِی بشینیم رودررو راجع‌بهش حرف بزنیم؟",
        why="حقِ خواستنِ وضوح را تأیید می‌کند؛ تمایل به شفافیت را می‌گوید بدون وعده‌ی توخالی؛ به قدمِ مشخص دعوت می‌کند.",
    ),
    GoldenExample(
        id="comparison",
        situation="مقایسه با دیگران",
        user_goal="calm_conflict",
        incoming="دوستِ من ببین چطوری هواشو داره. تو کِی انقدر برام وقت گذاشتی؟",
        reply="می‌بینم که دلت می‌خواد بیشتر برات وقت بذارم و حقته. نمی‌خوام با کسی مقایسه شیم، ولی حرفِ اصلیتو گرفتم. بگو چجوری بودنم کنارت برات بهتر می‌شه؟",
        why="نیازِ پشتِ مقایسه را می‌بیند؛ بی‌آنکه جبهه بگیرد مرزِ نرمِ مقایسه‌نکردن می‌گذارد؛ سوالِ سازنده می‌پرسد.",
    ),
    GoldenExample(
        id="testing_breakup",
        situation="محک‌زدن با تهدیدِ جدایی",
        user_goal="calm_conflict",
        incoming="اگه بگم بیا تمومش کنیم چی؟",
        reply="حس می‌کنم این حرف بیشتر از سرِ دلخوریه تا اینکه واقعاً بخوای. من نمی‌خوام تمومش کنم. بگو چی انقدر اذیتت کرده که به اینجا رسیدی؟",
        why="پشتِ تهدید (دلخوری) را می‌خواند بدون قطعیت؛ موضعِ خودش را صادقانه می‌گوید؛ ریشه را می‌پرسد، نه واکنشِ ترس.",
    ),
    GoldenExample(
        id="one_word_cold",
        situation="جوابِ تک‌کلمه‌ایِ سرد",
        user_goal="calm_conflict",
        incoming="باشه.",
        reply="این «باشه»‌ت یه جوری بود. حس می‌کنم یه چیزی هست. اگه بگی چی شده، خیالم راحت‌تره.",
        why="سردیِ پیام را مستقیم اما نرم نام می‌برد؛ بدون فرض بد، حس را می‌گوید؛ بدون فشار در را باز می‌کند.",
    ),
    GoldenExample(
        id="avoid_needy_they_went_quiet",
        situation="طرف ساکت شده و کاربر نمی‌خواهد آویزان دیده شود",
        user_goal="avoid_needy",
        incoming="(چند ساعته جواب نداده و آنلاین بوده)",
        reply="هر وقت سرت خلوت شد یه خبر بده، کاری باهات داشتم. عجله‌ای نیست. منتظرتم.",
        why="تماس را برقرار می‌کند بدون گله یا اضطراب؛ توپ را زمینِ طرف می‌گذارد بی‌آنکه نیازمند دیده شود؛ کوتاه و خونسرد.",
    ),
    GoldenExample(
        id="avoid_needy_double_text_urge",
        situation="میلِ کاربر به پشت‌سرهم پیام‌دادن بعد از بی‌جوابی",
        user_goal="avoid_needy",
        incoming="(پیام قبلی کاربر بی‌جواب مانده و وسوسه‌ی پیامِ دوم دارد)",
        reply="راستی یه چیزی یادم رفت بگم؛ هر وقت دیدی پیامو جواب بده. روزت خوب باشه.",
        why="به‌جای پیامِ گله‌مندِ دوم، یک پیامِ سبک و بی‌فشار می‌فرستد؛ نیاز و اضطراب نشان نمی‌دهد؛ در را باز و آرام نگه می‌دارد.",
    ),
    GoldenExample(
        id="seen_story_no_reply",
        situation="استوری را دیده ولی جواب پیام نداده",
        user_goal="avoid_needy",
        incoming="استوریمو دیدی ولی جوابِ پیاممو ندادی. باشه فهمیدم.",
        reply="ندیده بودم پیامتو راستش، الان چشمم خورد. چی شده؟ بگو می‌شنوم.",
        why="بدون حالتِ تدافعی، کوتاه توضیح می‌دهد (نه بهانه‌ی طولانی)؛ آویزان به نظر نمی‌رسد؛ مستقیم به اصل می‌رود.",
    ),
    GoldenExample(
        id="always_first",
        situation="گله از اینکه همیشه کاربر باید پیش‌قدم شود",
        user_goal="avoid_needy",
        incoming="انگار همیشه باید من پیش‌قدم شم. تو هیچ‌وقت اول پیام نمیدی.",
        reply="حق داری، حواسم به این نبوده و باید بیشتر اول قدم بردارم. از این به بعد بیشتر خودم بهت سر می‌زنم. الانم دلم می‌خواست صدات رو بشنوم.",
        why="گله را بدون دفاع می‌پذیرد و سهم می‌گیرد؛ تغییرِ مشخص می‌گوید نه وعده‌ی کلی؛ گرمیِ واقعی نشان می‌دهد.",
    ),
    GoldenExample(
        id="passive_aggressive_fine",
        situation="منفعل-پرخاشگرِ «هرجور راحتی»",
        user_goal="calm_conflict",
        incoming="نه خوبه، هرجور راحتی. مهم نظرِ توئه دیگه.",
        reply="حس می‌کنم اینو از سرِ دلخوری میگی، نه واقعاً. برام مهمه که نظرِ تو هم باشه، جدی میگم. بگو خودت چی دوست داری؟",
        why="پشتِ «هرجور راحتی» را می‌خواند؛ بی‌آنکه تسلیمِ طعنه شود اهمیتِ نظرِ طرف را می‌گوید؛ مستقیم نظرش را می‌پرسد.",
    ),
    GoldenExample(
        id="not_priority",
        situation="حسِ در اولویت‌نبودن",
        user_goal="calm_conflict",
        incoming="حس میکنم هیچ‌وقت اولویتت نیستم. همیشه یه چیزی مهم‌تر از منه.",
        reply="نمی‌خوام این حسو داشته باشی چون واقعاً برام مهمی. شاید درست نشون ندادم جایگاهتو پیشم. بگو چی کار کنم که این حس عوض شه؟",
        why="حسِ اولویت‌نبودن را آرام می‌کند بدون «حق با توئه»؛ سهمِ نشان‌ندادن را می‌پذیرد؛ سوالِ عملی و باز می‌پرسد.",
    ),
    GoldenExample(
        id="miss_you_but_hurt",
        situation="دلتنگی همراه با دلخوری (نیمه‌آشتی)",
        user_goal="calm_conflict",
        incoming="دلم برات تنگ شده ولی هنوز از دستت ناراحتم.",
        reply="منم دلم برات تنگ شده، خیلی. می‌دونم هنوز دلخوری و عجله‌ای برای رد شدن ازش ندارم. بیا هم دلتنگی رو ببینیم هم اون دلخوری رو با هم حل کنیم.",
        why="قدمِ نرمِ دلتنگی را گرم می‌گیرد؛ دلخوری را انکار نمی‌کند و فضا می‌دهد؛ هر دو حس را با هم به جلو می‌برد.",
    ),
]


def select_golden_examples(
    relationship_type: str,
    user_goal: str,
    limit: int = 4,
) -> list[GoldenExample]:
    """Return the most relevant golden examples for the given wedge cell.

    Only the romantic wedge is covered; other relationship types get an empty
    list so the generic path is unaffected. Examples whose ``user_goal`` matches
    are preferred, then the rest of the wedge fills up to ``limit`` so the model
    always sees a few exemplars of the target tone.
    """
    if relationship_type != WEDGE_RELATIONSHIP:
        return []
    matching = [ex for ex in GOLDEN_EXAMPLES if ex.user_goal == user_goal]
    others = [ex for ex in GOLDEN_EXAMPLES if ex.user_goal != user_goal]
    selected = (matching + others)[: max(0, limit)]
    return selected


def golden_examples_for_prompt(
    relationship_type: str,
    user_goal: str,
    limit: int = 4,
) -> list[dict[str, str]]:
    """Compact (incoming -> ideal_reply) pairs ready to embed in the prompt."""
    return [
        {"پیام_دریافتی": ex.incoming, "جوابِ_طلایی": ex.reply}
        for ex in select_golden_examples(relationship_type, user_goal, limit)
    ]
