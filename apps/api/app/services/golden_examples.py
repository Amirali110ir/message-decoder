"""Golden few-shot examples, organised by relationship type.

Each example is a hand-approved pair of (incoming message -> ideal reply) that
embodies the form + content rules of the v0.4 system prompt:

  Form    : for personal relationships, shekaste (colloquial), short (1-3
            chat-sized sentences), direct, "تو" address, no psychology jargon.
            For work/customer, professional "شما", short, accountable.
  Content : settle the feeling before logic; validate the feeling, not the
            claim; be specific, not general; NO defensive excuse (never
            "سرم شلوغ بود" / "درگیر کاری بودم"); catch the other person's soft
            step; leave an open door, not a demand.
  Structure: sentence 1 disarms the threat, sentence 2 states your position
            without defending, sentence 3 leaves a door open.

They are injected into the paid prompt as few-shot exemplars (see
``select_golden_examples`` / ``golden_examples_as_messages``). Selection scopes
to the message's ``relationship_type`` first, then prefers the matching
``user_goal`` so the model always sees a few exemplars of the target tone.

Golden rule honoured by every reply here: help the user be more honest and
clear, never to manipulate or guilt-trip the other person.

--- Goal semantics for the ``reply`` field ---

  calm_conflict       : de-escalate; 1-3 sentences; acknowledge feeling then state
                        position without defending; leave a door open.
  avoid_needy         : brief, warm, zero pressure; hand the next move to the other
                        person; do NOT chase or apologise.
  set_boundary        : name the limit clearly but without attack; keep the door open
                        for a healthier version of the interaction.
  end_conversation    : close the loop without cruelty; name the reason (exhaustion /
                        circularity) and offer a future re-open if genuine.
  make_them_accountable: no accusation of character; name the specific broken agreement;
                        ask for a concrete date/action, not an apology.
  improve_relationship: catch the soft step; reciprocate warmth; convert the moment into
                        a small, sustainable forward action.
  professional_reply  : direct, time-bound, accountable; no emotional over-explaining.
  understand_only     : the user primarily wants to decode the message, not necessarily
                        reply. ``reply`` holds the *minimal safe fallback* — the one
                        sentence that is honest, non-escalating, and neither opens nor
                        slams a door. Keep it to ≤ 2 sentences; do NOT volunteer
                        information the user did not ask about.
"""

from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GoldenExample:
    id: str
    relationship_type: str   # "romantic" | "ex" | "manager_colleague" | "customer" | "family" | "friend"
    situation: str           # short tag describing the incoming-message type
    user_goal: str
    incoming: str            # the message the user received
    reply: str               # the ideal, copy-ready reply
    why: str                 # why this reply is good (not sent to the model verbatim)


# ───────────────────────── romantic ─────────────────────────
# The original wedge: highest coverage, calm_conflict / avoid_needy plus
# set_boundary / end_conversation (so those goals no longer borrow softer
# calm_conflict exemplars).
_ROMANTIC: list[GoldenExample] = [
    GoldenExample(
        id="cold_dismissal",
        relationship_type="romantic",
        situation="کناره‌گیریِ سرد و قهرآلود",
        user_goal="calm_conflict",
        incoming="باشه دیگه. معلومه که سرت شلوغه. منم دیگه مزاحم نمیشم.",
        reply="مزاحم چیه آخه. الان حواسم کاملاً بهته. بگو چی شد که این حسو پیدا کردی.",
        why="تهدید را خاموش می‌کند («مزاحم چیه») بدون بهانه‌آوردن برای دیرکرد؛ موضع گرم را مشخص می‌گوید؛ در باز می‌گذارد بدون بازجویی.",
    ),
    GoldenExample(
        id="late_reply_complaint",
        relationship_type="romantic",
        situation="گله از دیر جواب دادن",
        user_goal="calm_conflict",
        incoming="چرا انقدر دیر جواب میدی؟ انگار اصلا برات مهم نیست.",
        reply="می‌فهمم چرا این حسو داری و دوست ندارم اینطوری فکر کنی. تو برام مهمی، خیلی هم مهمی. بیا یه قرار بذاریم سرفرصت حرف بزنیم.",
        why="حس را می‌بیند بدون اینکه «حق با توئه» بگوید؛ موضع را مستقیم و بدون بهانه‌ی دیرکرد می‌گوید؛ یک قدم مشخص پیشنهاد می‌دهد.",
    ),
    GoldenExample(
        id="vague_nevermind",
        relationship_type="romantic",
        situation="پیامِ مبهم و سربسته",
        user_goal="calm_conflict",
        incoming="هیچی. ولش کن. مهم نیست.",
        reply="حس می‌کنم یه چیزی هست که اذیتت کرده. برام مهمه بدونم، جدی میگم. هر وقت آماده بودی بگو، عجله‌ای نیست.",
        why="پشتِ «ولش کن» را می‌بیند؛ اهمیت‌دادن را مشخص می‌گوید؛ بدون فشار در را باز می‌گذارد.",
    ),
    GoldenExample(
        id="sarcasm",
        relationship_type="romantic",
        situation="کنایه و طعنه",
        user_goal="calm_conflict",
        incoming="نه بابا، تو که همیشه سرت شلوغه. ما کجا و وقتِ تو کجا.",
        reply="انگار حسابی دلت پره ازم. کنایه نزنیم بهتره، چون دوست دارم واقعاً بفهمم چی شده. بگو کجا کم گذاشتم؟",
        why="طعنه را آرام به رسمیت می‌شناسد بدون اینکه جبهه بگیرد؛ مرزِ نرمِ «کنایه نزنیم» می‌گذارد؛ مستقیم دعوت به اصل ماجرا می‌کند.",
    ),
    GoldenExample(
        id="jealousy",
        relationship_type="romantic",
        situation="حسادت و سوال‌پیچ",
        user_goal="calm_conflict",
        incoming="با کی بودی که جواب نمیدادی؟ چرا آنلاین بودی ولی جواب من رو ندادی؟",
        reply="می‌بینم که نگران شدی و این حسو دوست ندارم بینمون باشه. چیزی نبوده که بخوام ازت پنهون کنم. بیا حرف بزنیم تا این نگرانی نمونه تو دلت.",
        why="نگرانی را می‌بیند نه اتهام را؛ شفافیت را بدون حالتِ تدافعی می‌گوید؛ به‌جای پاسخِ بازجویی، گفتگو پیشنهاد می‌کند.",
    ),
    GoldenExample(
        id="long_silence_then_ping",
        relationship_type="romantic",
        situation="سکوتِ طولانی و بعد یک پیامِ کوتاه",
        user_goal="calm_conflict",
        incoming="زنده‌ای؟",
        reply="آره هستم، ببخش که این چند وقت کم پیدا بودم. دلم برات تنگ شده بود راستش. چطوری تو؟",
        why="بدون توجیهِ طولانی، کوتاه عذرِ غیبت را می‌گیرد (نه بهانه)؛ گرمی نشان می‌دهد؛ در را برای ادامه باز می‌کند.",
    ),
    GoldenExample(
        id="their_half_apology",
        relationship_type="romantic",
        situation="عذرخواهیِ نیمه از طرف مقابل",
        user_goal="calm_conflict",
        incoming="ببخشید اگه دیشب تند رفتم. نمیدونم چرا یهو عصبی شدم.",
        reply="مرسی که گفتی، واقعاً برام ارزش داره. منم دیشب می‌تونستم آروم‌تر باشم. مهم اینه که الان خوبیم.",
        why="قدمِ نرمِ طرف را با گرمی می‌گیرد و خنثی نمی‌کند؛ سهمِ کوچک خودش را بدون خودزنی می‌پذیرد؛ رو به جلو می‌بندد.",
    ),
    GoldenExample(
        id="guilt_trip",
        relationship_type="romantic",
        situation="گناه‌اندازی",
        user_goal="calm_conflict",
        incoming="من هرکاری میکنم بازم برات کمه. انگار هیچ‌وقت کافی نیستم.",
        reply="اصلاً دوست ندارم همچین حسی داشته باشی، چون برام کم نیستی. شاید من خوب نشون ندادم چقدر برام مهمی. بگو چی باعث شده این حسو پیدا کنی؟",
        why="حسِ «کافی نبودن» را آرام می‌کند بدون اینکه وارد بازیِ گناه شود؛ سهمِ خودش را در نشان‌ندادن می‌پذیرد؛ سوالِ باز می‌پرسد.",
    ),
    GoldenExample(
        id="withdrawal",
        relationship_type="romantic",
        situation="بی‌حسی و فاصله‌گرفتن",
        user_goal="calm_conflict",
        incoming="دیگه حسش نیست. خسته شدم از این رابطه.",
        reply="این حرفت برام سنگینه، ولی می‌خوام بفهممش نه اینکه ازش فرار کنم. حس می‌کنم خیلی خسته‌ای. می‌تونیم آروم درباره‌ش حرف بزنیم؟",
        why="سنگینیِ پیام را به رسمیت می‌شناسد بدون وحشت‌زدگی یا التماس؛ خستگیِ طرف را می‌بیند؛ گفتگوی آرام پیشنهاد می‌کند.",
    ),
    GoldenExample(
        id="accusation_selfish",
        relationship_type="romantic",
        situation="اتهامِ خودخواهی",
        user_goal="calm_conflict",
        incoming="تو اصلا به فکر من نیستی. فقط به خودت فکر میکنی.",
        reply="می‌فهمم که الان این حسو داری و برام مهمه. من اینطوری نمی‌بینمت، ولی شاید جایی کم گذاشتم که این حس بهت دست داده. کجا بود که حس کردی به فکرت نیستم؟",
        why="حس را می‌بیند بدون تأییدِ اتهام؛ موضع را روشن می‌گوید و فضای پذیرشِ سهم می‌گذارد؛ مشخص می‌پرسد، نه کلی.",
    ),
    GoldenExample(
        id="pressure_define",
        relationship_type="romantic",
        situation="فشار برای روشن‌کردنِ تکلیف",
        user_goal="calm_conflict",
        incoming="بالاخره تکلیف منو روشن کن. نمیتونم همینطوری بلاتکلیف بمونم.",
        reply="حق داری بخوای بدونی کجای کاریم، این بلاتکلیفی سخته. منم می‌خوام روشن حرف بزنیم نه نصفه. کِی بشینیم رودررو راجع‌بهش حرف بزنیم؟",
        why="حقِ خواستنِ وضوح را تأیید می‌کند؛ تمایل به شفافیت را می‌گوید بدون وعده‌ی توخالی؛ به قدمِ مشخص دعوت می‌کند.",
    ),
    GoldenExample(
        id="comparison",
        relationship_type="romantic",
        situation="مقایسه با دیگران",
        user_goal="calm_conflict",
        incoming="دوستِ من ببین چطوری هواشو داره. تو کِی انقدر برام وقت گذاشتی؟",
        reply="می‌بینم که دلت می‌خواد بیشتر برات وقت بذارم و حقته. نمی‌خوام با کسی مقایسه شیم، ولی حرفِ اصلیتو گرفتم. بگو چجوری بودنم کنارت برات بهتر می‌شه؟",
        why="نیازِ پشتِ مقایسه را می‌بیند؛ بی‌آنکه جبهه بگیرد مرزِ نرمِ مقایسه‌نکردن می‌گذارد؛ سوالِ سازنده می‌پرسد.",
    ),
    GoldenExample(
        id="testing_breakup",
        relationship_type="romantic",
        situation="محک‌زدن با تهدیدِ جدایی",
        user_goal="calm_conflict",
        incoming="اگه بگم بیا تمومش کنیم چی؟",
        reply="حس می‌کنم این حرف بیشتر از سرِ دلخوریه تا اینکه واقعاً بخوای. من نمی‌خوام تمومش کنم. بگو چی انقدر اذیتت کرده که به اینجا رسیدی؟",
        why="پشتِ تهدید (دلخوری) را می‌خواند بدون قطعیت؛ موضعِ خودش را صادقانه می‌گوید؛ ریشه را می‌پرسد، نه واکنشِ ترس.",
    ),
    GoldenExample(
        id="one_word_cold",
        relationship_type="romantic",
        situation="جوابِ تک‌کلمه‌ایِ سرد",
        user_goal="calm_conflict",
        incoming="باشه.",
        reply="این «باشه»‌ت یه جوری بود. حس می‌کنم یه چیزی هست. اگه بگی چی شده، خیالم راحت‌تره.",
        why="سردیِ پیام را مستقیم اما نرم نام می‌برد؛ بدون فرض بد، حس را می‌گوید؛ بدون فشار در را باز می‌کند.",
    ),
    GoldenExample(
        id="avoid_needy_they_went_quiet",
        relationship_type="romantic",
        situation="طرف ساکت شده و کاربر نمی‌خواهد آویزان دیده شود",
        user_goal="avoid_needy",
        incoming="(چند ساعته جواب نداده و آنلاین بوده)",
        reply="هر وقت سرت خلوت شد یه خبر بده، کاری باهات داشتم. عجله‌ای نیست. منتظرتم.",
        why="تماس را برقرار می‌کند بدون گله یا اضطراب؛ توپ را زمینِ طرف می‌گذارد بی‌آنکه نیازمند دیده شود؛ کوتاه و خونسرد.",
    ),
    GoldenExample(
        id="avoid_needy_double_text_urge",
        relationship_type="romantic",
        situation="میلِ کاربر به پشت‌سرهم پیام‌دادن بعد از بی‌جوابی",
        user_goal="avoid_needy",
        incoming="(پیام قبلی کاربر بی‌جواب مانده و وسوسه‌ی پیامِ دوم دارد)",
        reply="راستی یه چیزی یادم رفت بگم؛ هر وقت دیدی پیامو جواب بده. روزت خوب باشه.",
        why="به‌جای پیامِ گله‌مندِ دوم، یک پیامِ سبک و بی‌فشار می‌فرستد؛ نیاز و اضطراب نشان نمی‌دهد؛ در را باز و آرام نگه می‌دارد.",
    ),
    GoldenExample(
        id="seen_story_no_reply",
        relationship_type="romantic",
        situation="استوری را دیده ولی جواب پیام نداده",
        user_goal="avoid_needy",
        incoming="استوریمو دیدی ولی جوابِ پیاممو ندادی. باشه فهمیدم.",
        reply="ندیده بودم پیامتو راستش، الان چشمم خورد. چی شده؟ بگو می‌شنوم.",
        why="بدون حالتِ تدافعی، کوتاه توضیح می‌دهد (نه بهانه‌ی طولانی)؛ آویزان به نظر نمی‌رسد؛ مستقیم به اصل می‌رود.",
    ),
    GoldenExample(
        id="always_first",
        relationship_type="romantic",
        situation="گله از اینکه همیشه کاربر باید پیش‌قدم شود",
        user_goal="avoid_needy",
        incoming="انگار همیشه باید من پیش‌قدم شم. تو هیچ‌وقت اول پیام نمیدی.",
        reply="حق داری، حواسم به این نبوده و باید بیشتر اول قدم بردارم. از این به بعد بیشتر خودم بهت سر می‌زنم. الانم دلم می‌خواست صدات رو بشنوم.",
        why="گله را بدون دفاع می‌پذیرد و سهم می‌گیرد؛ تغییرِ مشخص می‌گوید نه وعده‌ی کلی؛ گرمیِ واقعی نشان می‌دهد.",
    ),
    GoldenExample(
        id="passive_aggressive_fine",
        relationship_type="romantic",
        situation="منفعل-پرخاشگرِ «هرجور راحتی»",
        user_goal="calm_conflict",
        incoming="نه خوبه، هرجور راحتی. مهم نظرِ توئه دیگه.",
        reply="حس می‌کنم اینو از سرِ دلخوری میگی، نه واقعاً. برام مهمه که نظرِ تو هم باشه، جدی میگم. بگو خودت چی دوست داری؟",
        why="پشتِ «هرجور راحتی» را می‌خواند؛ بی‌آنکه تسلیمِ طعنه شود اهمیتِ نظرِ طرف را می‌گوید؛ مستقیم نظرش را می‌پرسد.",
    ),
    GoldenExample(
        id="not_priority",
        relationship_type="romantic",
        situation="حسِ در اولویت‌نبودن",
        user_goal="calm_conflict",
        incoming="حس میکنم هیچ‌وقت اولویتت نیستم. همیشه یه چیزی مهم‌تر از منه.",
        reply="نمی‌خوام این حسو داشته باشی چون واقعاً برام مهمی. شاید درست نشون ندادم جایگاهتو پیشم. بگو چی کار کنم که این حس عوض شه؟",
        why="حسِ اولویت‌نبودن را آرام می‌کند بدون «حق با توئه»؛ سهمِ نشان‌ندادن را می‌پذیرد؛ سوالِ عملی و باز می‌پرسد.",
    ),
    GoldenExample(
        id="miss_you_but_hurt",
        relationship_type="romantic",
        situation="دلتنگی همراه با دلخوری (نیمه‌آشتی)",
        user_goal="calm_conflict",
        incoming="دلم برات تنگ شده ولی هنوز از دستت ناراحتم.",
        reply="منم دلم برات تنگ شده، خیلی. می‌دونم هنوز دلخوری و عجله‌ای برای رد شدن ازش ندارم. بیا هم دلتنگی رو ببینیم هم اون دلخوری رو با هم حل کنیم.",
        why="قدمِ نرمِ دلتنگی را گرم می‌گیرد؛ دلخوری را انکار نمی‌کند و فضا می‌دهد؛ هر دو حس را با هم به جلو می‌برد.",
    ),
    # --- set_boundary (T8) ---
    GoldenExample(
        id="rom_insult_boundary",
        relationship_type="romantic",
        situation="توهین در اوج عصبانیت",
        user_goal="set_boundary",
        incoming="تو یه خودخواه به تمام معنایی، حالم ازت بهم می‌خوره.",
        reply="می‌بینم خیلی عصبانی‌ای و حق داری ناراحت باشی. ولی با این لحن نمی‌تونم ادامه بدم. هر وقت آروم‌تر شدی، آماده‌ام حرف بزنیم.",
        why="خشم را به رسمیت می‌شناسد بدون تأییدِ توهین؛ مرزِ روشنِ لحن را بدون تحقیرِ متقابل می‌گذارد؛ درِ گفتگوی سالم را باز نگه می‌دارد.",
    ),
    GoldenExample(
        id="rom_phone_control_boundary",
        relationship_type="romantic",
        situation="درخواست کنترل‌گرانه‌ی رمز گوشی",
        user_goal="set_boundary",
        incoming="باید رمز گوشیتو بهم بدی، اگه چیزی واسه پنهون کردن نداری.",
        reply="می‌فهمم که می‌خوای مطمئن شی، ولی گوشیم یه حریم شخصیه که نمی‌خوام ازش بگذرم. بیا روی اعتمادمون کار کنیم نه روی چک کردن.",
        why="نیازِ پشتِ کنترل (اطمینان) را می‌بیند؛ مرزِ حریم را قاطع اما بدون تحقیر نگه می‌دارد؛ مسیر سالم (اعتماد) را پیشنهاد می‌کند.",
    ),
    GoldenExample(
        id="rom_excessive_calls_boundary",
        relationship_type="romantic",
        situation="تماس‌های پشت‌سرهم و بازخواست",
        user_goal="set_boundary",
        incoming="چرا جواب نمیدی؟ بیست بار زنگ زدم، کجایی؟",
        reply="می‌بینم که نگرانم شدی و ببخشید بابتش. ولی این همه تماس یه‌کم اذیتم می‌کنه؛ بیا یه راه راحت‌تر برای خبر دادن پیدا کنیم.",
        why="نگرانی را می‌بیند بدون بهانه‌آوردن؛ ناراحتیِ خودش از حجمِ تماس را مستقیم می‌گوید؛ به‌جای دعوا، راه‌حلِ مشترک پیشنهاد می‌کند.",
    ),
    # --- end_conversation (T8) ---
    GoldenExample(
        id="rom_circular_fight_end",
        relationship_type="romantic",
        situation="دعوای دوّار و تکراری",
        user_goal="end_conversation",
        incoming="بازم همون حرفا، تو هیچ‌وقت عوض نمیشی.",
        reply="حس می‌کنم داریم یه دور باطلو تکرار می‌کنیم و جفتمون خسته‌ایم. بیا الان تمومش کنیم و سرحال‌تر که شدیم ادامه بدیم.",
        why="چرخه را بدون مقصریابی نام می‌برد؛ خستگیِ مشترک را می‌بیند؛ پایانِ نرم با درِ بازِ بعدی می‌گذارد، نه قهر.",
    ),
    GoldenExample(
        id="rom_2am_drained_end",
        relationship_type="romantic",
        situation="اصرار به ادامه‌ی بحث تا صبح",
        user_goal="end_conversation",
        incoming="تا صبح باید حرف بزنیم تا حل شه.",
        reply="این موضوع برام مهمه، ولی الان هردومون خسته‌ایم و حرفا داره تند میشه. بذار فردا با ذهن آروم حلش کنیم.",
        why="اهمیتِ موضوع را انکار نمی‌کند؛ دلیلِ توقف (خستگی و تند شدن) را شفاف می‌گوید؛ زمانِ مشخصِ ازسرگیری می‌دهد.",
    ),
    GoldenExample(
        id="rom_talking_to_wall_end",
        relationship_type="romantic",
        situation="حسِ شنیده‌نشدن و کلافگی",
        user_goal="end_conversation",
        incoming="هرچی می‌گم انگار با دیوار حرف می‌زنم.",
        reply="می‌بینم که چقدر کلافه‌ای و نمی‌خوام بیشتر بشه. بیا فعلاً یه مکث کنیم، بعداً سرحال‌تر برمی‌گردیم سرش.",
        why="کلافگی را می‌بیند بدون جبهه‌گیری؛ مکث را به‌جای تسلیم یا جنگ پیشنهاد می‌کند؛ ادامه را به جلو موکول می‌کند.",
    ),
    # --- improve_relationship ---
    GoldenExample(
        id="romantic_improve_emotional_distance",
        relationship_type="romantic",
        situation="ابراز فاصله‌ی عاطفی توسط پارتنر",
        user_goal="improve_relationship",
        incoming="حس می‌کنم این روزا فقط کنار همیم، ولی با هم نیستیم.",
        reply="خوشحالم که گفتیش، چون خودمم یه همچین حسی داشتم. امشب بیا گوشیا رو بذاریم کنار و فقط با هم حرف بزنیم.",
        why="Mirrors the vulnerable move warmly (rule 4), admits shared feeling without defensiveness, ends with a concrete invitation not a vague promise.",
    ),
    GoldenExample(
        id="romantic_improve_gratitude_mirror",
        relationship_type="romantic",
        situation="قدردانی احساسی پارتنر",
        user_goal="improve_relationship",
        incoming="ممنون که دیروز کنارم بودی. خیلی وقت بود کسی اینجوری حواسش بهم نبود.",
        reply="این حرفت خیلی به دلم نشست. دوست دارم از این لحظه‌ها بیشتر داشته باشیم؛ تو هم بگو چیا حالتو خوب می‌کنه.",
        why="Catches the soft step and reciprocates instead of deflecting; turns a one-off moment into a pattern by inviting specificity.",
    ),
    GoldenExample(
        id="romantic_improve_decision_complaint",
        relationship_type="romantic",
        situation="گلایه از تصمیم‌گیری یک‌طرفه",
        user_goal="improve_relationship",
        incoming="تو هیچ‌وقت نظر منو نمی‌پرسی، خودت تصمیم می‌گیری.",
        reply="راست میگی، چند بار همین‌جوری شده. از این به بعد قبلش باهات چک می‌کنم؛ الانم بگو کجاها بیشتر اذیتت کرد.",
        why="Validates the claim where it's actually true (no fake validation), commits to a specific behavioral change, asks for specifics instead of a general 'let's talk'.",
    ),
]


# ───────────────────────── ex ─────────────────────────
# Highest-risk gap: a bad reply here reopens a closed door or sends an
# ambiguous signal. Style = neutral, respectful, short, no nostalgia, no
# therapist role, no reopening unless intended.
_EX: list[GoldenExample] = [
    GoldenExample(
        id="ex_wants_to_meet",
        relationship_type="ex",
        situation="درخواستِ دیدارِ دوباره",
        user_goal="set_boundary",
        incoming="میشه یه بار دیگه ببینمت؟ فقط حرف بزنیم.",
        reply="حرفات رو می‌شنوم، ولی فکر نمی‌کنم دیدنِ همدیگه الان به جفتمون کمک کنه. اگه چیزِ مشخصی هست، همینجا بگو.",
        why="بدون سردیِ توهین‌آمیز نه می‌گوید؛ درِ ابهام (دیدار) را می‌بندد؛ یک مسیرِ عملیِ محدود باز می‌گذارد.",
    ),
    GoldenExample(
        id="ex_blame_past",
        relationship_type="ex",
        situation="سرزنش بابتِ گذشته",
        user_goal="calm_conflict",
        incoming="تو زندگیمو خراب کردی و حالا راحت زندگی می‌کنی.",
        reply="می‌دونم هنوز ازم دلخوری و درکش می‌کنم. نمی‌خوام وارد بحثِ گذشته بشم، ولی واقعاً برات آرزوی خوب دارم.",
        why="دلخوری را به رسمیت می‌شناسد بدون پذیرشِ کاملِ اتهام؛ از بحثِ فرسایشیِ گذشته خارج می‌شود؛ با حسنِ نیت می‌بندد.",
    ),
    GoldenExample(
        id="ex_late_night_lonely",
        relationship_type="ex",
        situation="پیامِ شبانه از سرِ تنهایی",
        user_goal="set_boundary",
        incoming="بیداری؟ دلم گرفته.",
        reply="متاسفم که حالت خوب نیست. ولی بهتره برای این حرفا سراغِ یه نفرِ نزدیک‌تر بری؛ من دیگه جای درستی براش نیستم.",
        why="همدلیِ کوتاه نشان می‌دهد بدون باز کردنِ نقشِ همدمِ شبانه؛ مرز را روشن اما محترمانه می‌گذارد؛ ابهام نمی‌سازد.",
    ),
    GoldenExample(
        id="ex_pickup_belongings",
        relationship_type="ex",
        situation="هماهنگیِ عملیِ وسایل",
        user_goal="understand_only",
        incoming="اون وسایلت هنوز خونه‌ست، کی میای ببری؟",
        reply="ممنون که گفتی. آخرِ همین هفته هماهنگ می‌کنم یه نفر بیاد ببره که لازم نباشه همدیگه رو ببینیم.",
        why="مسئله‌ی عملی را عملی جواب می‌دهد؛ تماسِ حضوریِ غیرضروری را حذف می‌کند؛ کوتاه و بی‌ابهام.",
    ),
    GoldenExample(
        id="ex_nostalgia",
        relationship_type="ex",
        situation="یادآوریِ خاطراتِ خوب",
        user_goal="set_boundary",
        incoming="یادته پارسال همین موقع کجا بودیم؟ چقدر خوب بود.",
        reply="خاطره‌های خوبی بود، انکارش نمی‌کنم. ولی ترجیح می‌دم به گذشته برنگردیم. امیدوارم روزات خوب باشه.",
        why="نوستالژی را نه تأیید می‌کند نه تحقیر؛ مرزِ «برنگردیم» را نرم می‌گذارد؛ بدون باز کردنِ در می‌بندد.",
    ),
    GoldenExample(
        id="ex_calls_coldhearted",
        relationship_type="ex",
        situation="حمله‌ی عاطفیِ فرسایشی",
        user_goal="end_conversation",
        incoming="اصلا انگار نه انگار چند سال با هم بودیم. خیلی سنگدلی.",
        reply="نمی‌خوام بی‌احترامی کنم، ولی این گفتگو داره فرسایشی میشه. بهتره همینجا تمومش کنیم.",
        why="بدون دفاع یا تلافی، فرسایشی‌بودن را نام می‌برد؛ پایانِ محترمانه می‌گذارد؛ وارد چرخه‌ی اتهام نمی‌شود.",
    ),
    GoldenExample(
        id="ex_reconcile_test",
        relationship_type="ex",
        situation="محک‌زدن برای برگشت",
        user_goal="set_boundary",
        incoming="فکر کنم اشتباه کردیم جدا شدیم. تو چی فکر می‌کنی؟",
        reply="می‌فهمم که الان این حسو داری. من تصمیمم رو گرفتم و دوست ندارم دوباره بازش کنم. مراقبِ خودت باش.",
        why="حسِ طرف را می‌بیند بدون امیدِ کاذب؛ تصمیم را قاطع اما بی‌تحقیر می‌گوید؛ ابهام و در بازِ ناخواسته نمی‌سازد.",
    ),
    GoldenExample(
        id="ex_guilt_no_one_else",
        relationship_type="ex",
        situation="گناه‌اندازی با مسئولیتِ حالِ طرف",
        user_goal="set_boundary",
        incoming="به خاطر تو هنوز نتونستم با کسی باشم.",
        reply="متاسفم که این روزا برات سخت بوده. ولی مسئولیتِ حالِ الانت با خودته و من نمی‌تونم جای اون باشم.",
        why="همدلی نشان می‌دهد بدون پذیرشِ بارِ گناه؛ مسئولیت را محترمانه برمی‌گرداند؛ نقشِ نجات‌دهنده را رد می‌کند.",
    ),
    GoldenExample(
        id="ex_coparenting_logistics",
        relationship_type="ex",
        situation="هماهنگیِ فرزندِ مشترک",
        user_goal="professional_reply",
        incoming="بچه فردا مدرسه نمیاد؟ تو میبریش یا من؟",
        reply="من می‌برمش، نگران نباش. ساعت ۷:۳۰ آماده‌ست. اگه برنامه عوض شد خبر می‌دم.",
        why="کاملاً عملی و قابلِ اتکا؛ بدون بارِ عاطفی یا کنایه؛ زمان و قدمِ بعدی روشن.",
    ),
    GoldenExample(
        id="ex_drunk_text",
        relationship_type="ex",
        situation="پیامِ احساسی در حالِ غیرعادی",
        user_goal="set_boundary",
        incoming="دلم برات یه ذره شده لامصب.",
        reply="فکر کنم بهتره الان که حالت دستِ خودت نیست حرف نزنیم. صبح اگه چیزی بود بگو.",
        why="پاسخِ احساسیِ متقابل نمی‌دهد؛ مرز را بدون قضاوت می‌گذارد؛ تصمیم را به زمانِ هوشیاری موکول می‌کند.",
    ),
    GoldenExample(
        id="ex_threat_to_leave",
        relationship_type="ex",
        situation="تهدید به قطعِ همیشگیِ ارتباط",
        user_goal="end_conversation",
        incoming="اگه جواب ندی دیگه واسه همیشه میرم.",
        reply="هر تصمیمی که آرومت می‌کنه رو احترام می‌ذارم. مراقبِ خودت باش.",
        why="وارد بازیِ تهدید/التماس نمی‌شود؛ انتخابِ طرف را به خودش می‌سپارد؛ کوتاه و بدونِ سیگنالِ مبهم.",
    ),
    GoldenExample(
        id="ex_return_item_neutral",
        relationship_type="ex",
        situation="پیشنهادِ برگرداندنِ یک وسیله",
        user_goal="understand_only",
        incoming="گردنبندتو پیدا کردم، میخوای برات بفرستم؟",
        reply="ممنون که به فکرش بودی. آره اگه زحمتت نیست با پست بفرست، آدرسو می‌فرستم.",
        why="تشکرِ ساده بدون باز کردنِ گفتگوی عاطفی؛ راه‌حلِ غیرحضوری؛ خشک نیست ولی صمیمیِ گذشته هم نیست.",
    ),
    # --- calm_conflict ---
    GoldenExample(
        id="ex_calm_blame_message",
        relationship_type="ex",
        situation="پیام سرزنش‌آمیز اکس بعد از جدایی",
        user_goal="calm_conflict",
        incoming="تو زندگیمو نابود کردی و الان راحت داری زندگیتو می‌کنی.",
        reply="می‌بینم چقدر ازم دلخوری و نمی‌خوام این بحث داغ‌تر شه. برداشت من از اون رابطه فرق داره، ولی دعوا چیزی رو عوض نمی‌کنه.",
        why="Acknowledges the feeling without accepting the claim (rule 2), refuses the fight without coldness, and sends zero reopening signal.",
    ),
    GoldenExample(
        id="ex_calm_blocked_accusation",
        relationship_type="ex",
        situation="اتهام بی‌تفاوتی از طرف اکس",
        user_goal="calm_conflict",
        incoming="معلومه برات هیچ ارزشی نداشتم که انقدر راحت رد شدی.",
        reply="اینکه الان جوابم کوتاهه به معنی بی‌ارزش بودن اون دوران نیست. فقط فکر می‌کنم ادامه‌ی این بحث به هیچ‌کدوممون کمک نمی‌کنه.",
        why="Defuses the worth-attack without flattery or nostalgia; closes the argument loop while staying respectful — no ambiguity, no door to reopening.",
    ),
    # --- understand_only (minimal safe fallback) ---
    GoldenExample(
        id="ex_understand_dream_message",
        relationship_type="ex",
        situation="پیام نوستالژیک بی‌مقدمه از اکس",
        user_goal="understand_only",
        incoming="دیشب خوابتو دیدم. نمی‌دونم چرا، ولی گفتم بهت بگم.",
        reply="ممنون که گفتی. امیدوارم حالت خوب باشه.",
        why="Minimal, kind, and completely free of reopening signal — neither cold nor inviting; the decode matters more than the reply here.",
    ),
    GoldenExample(
        id="ex_understand_vague_closure_seek",
        relationship_type="ex",
        situation="سؤال مبهم اکس درباره‌ی دلیل جدایی",
        user_goal="understand_only",
        incoming="فقط می‌خوام بدونم واقعاً چی شد که اینجوری تموم شد.",
        reply="حرفت رو می‌فهمم و حق داری بخوای بدونی. دلیلش همونیه که موقع جدایی گفتم؛ چیز پنهونی وجود نداره.",
        why="Grants legitimate closure-seeking without re-litigating the relationship; refers back to the original conversation instead of opening a new one.",
    ),
]


# ───────────────────────── manager / colleague ─────────────────────────
# Professional "شما", documented, time-bound, no emotional overexplain, no
# sarcasm, no unrealistic promises.
_MANAGER: list[GoldenExample] = [
    GoldenExample(
        id="mgr_after_hours_task",
        relationship_type="manager_colleague",
        situation="درخواستِ کار خارج از ساعتِ اداری",
        user_goal="set_boundary",
        incoming="این گزارشو تا فردا صبح ساعت ۶ می‌خوام.",
        reply="حتماً انجامش می‌دم. چون الان خارج از ساعتِ کاریه، اول وقتِ صبح شروع می‌کنم و تا ساعت ۱۰ تحویلتون می‌دم؛ اگر زمانِ دقیق‌تری مدنظرتونه بفرمایید هماهنگ کنم.",
        why="مسئولیتِ کاری را می‌پذیرد؛ مرزِ ساعتِ کاری را بدون لحنِ شاکی می‌گذارد؛ زمانِ جایگزینِ مشخص و قابلِ مذاکره می‌دهد.",
    ),
    GoldenExample(
        id="mgr_public_blame",
        relationship_type="manager_colleague",
        situation="سرزنشِ عمومی بابتِ خروجی",
        user_goal="calm_conflict",
        incoming="تو جلسه گفتی این کارو کردی ولی هیچ خروجی‌ای نمی‌بینم.",
        reply="ممنون که مطرح کردید. خروجی تا دیروز آماده شده و لینکش رو همین الان خدمتتون می‌فرستم تا بررسی کنید.",
        why="بدون دفاعِ احساسی، با واقعیت پاسخ می‌دهد؛ قدمِ بعدیِ ملموس (لینک) می‌دهد؛ بحث را به مدرک منتقل می‌کند.",
    ),
    GoldenExample(
        id="colleague_passive_aggressive",
        relationship_type="manager_colleague",
        situation="کنایه‌ی همکار در جمع",
        user_goal="calm_conflict",
        incoming="بعضیا انگار فقط بلدن تو جلسه حرف بزنن.",
        reply="اگر درباره‌ی کاری بازخوردی دارید، خوشحال می‌شم مستقیم بشنوم تا بهترش کنم. هر جا کم گذاشتم بگید.",
        why="طعنه را به بازخوردِ مستقیم دعوت می‌کند؛ جبهه نمی‌گیرد؛ توپ را محترمانه به زمینِ شفافیت می‌اندازد.",
    ),
    GoldenExample(
        id="mgr_scope_creep",
        relationship_type="manager_colleague",
        situation="اضافه‌شدنِ کارِ بی‌برنامه",
        user_goal="set_boundary",
        incoming="اینم به لیست کارات اضافه کن، فکر کنم سریع باشه.",
        reply="می‌تونم این رو هم بردارم. فقط برای اینکه کیفیتِ بقیه کارها حفظ بشه، کمک می‌کنید اولویتش رو نسبت به تسکِ فعلی مشخص کنیم؟",
        why="نه نمی‌گوید ولی مرزِ ظرفیت را می‌گذارد؛ تصمیمِ اولویت را به مدیر برمی‌گرداند؛ حرفه‌ای و بدونِ دلخوری.",
    ),
    GoldenExample(
        id="colleague_excuse_accountability",
        relationship_type="manager_colleague",
        situation="بهانه‌ی همکار برای تأخیر",
        user_goal="make_them_accountable",
        incoming="ببخشید نشد انجامش بدم، یه کارایی پیش اومد.",
        reply="اشکالی نداره پیش میاد. فقط بگید تا کی می‌تونید تحویلش بدید که بتونم بقیه کارها رو بر اساسش بچینم؟",
        why="بدون سرزنش، مسئولیت را با درخواستِ زمانِ مشخص برمی‌گرداند؛ پیامد را طبیعی نشان می‌دهد؛ رابطه‌ی کاری را نمی‌سوزاند.",
    ),
    GoldenExample(
        id="mgr_vague_criticism",
        relationship_type="manager_colleague",
        situation="انتقادِ مبهمِ مدیر",
        user_goal="professional_reply",
        incoming="این اصلا اون چیزی نبود که می‌خواستم.",
        reply="ممنون از بازخورد. برای اینکه دقیق اصلاحش کنم، کدوم بخش بیشتر فاصله داشت با چیزی که مدنظرتون بود؟",
        why="دفاع نمی‌کند؛ انتقادِ کلی را به جزئیاتِ عملی تبدیل می‌کند؛ مسیرِ اصلاح را باز می‌کند.",
    ),
    GoldenExample(
        id="colleague_credit_taking",
        relationship_type="manager_colleague",
        situation="مصادره‌ی اعتبارِ کارِ مشترک",
        user_goal="set_boundary",
        incoming="تو جلسه گفتم ایده‌ی این پروژه مال من بود.",
        reply="خوشحالم که پروژه دیده شد. این ایده رو با هم جلو بردیم و فکر می‌کنم بهتره همین‌طور هم معرفیش کنیم.",
        why="شأن را بدون جنگِ قدرت برمی‌گرداند؛ واقعیتِ مشترک‌بودن را قاطع اما بی‌تحقیر می‌گوید؛ راهِ اصلاحِ روایت را باز می‌گذارد.",
    ),
    GoldenExample(
        id="mgr_weekend_message",
        relationship_type="manager_colleague",
        situation="پیامِ کاریِ آخرِ هفته",
        user_goal="set_boundary",
        incoming="آخر هفته یه سر به ایمیلت بزن، چندتا کار هست.",
        reply="حتماً. صبحِ شنبه اول وقت بهشون رسیدگی می‌کنم؛ اگر موردی فوریه همین الان بگید تا امروز ببینم.",
        why="در دسترس بودنِ معقول را نشان می‌دهد؛ مرزِ آخرِ هفته را بدونِ تقابل می‌گذارد؛ راهِ استثنای فوری را باز می‌گذارد.",
    ),
    GoldenExample(
        id="mgr_micromanage",
        relationship_type="manager_colleague",
        situation="کنترلِ بیش از حدِ مدیر",
        user_goal="calm_conflict",
        incoming="چرا هر کاری می‌کنی باید چند بار چک کنم؟",
        reply="متوجهم که می‌خواید مطمئن بشید کارها درست پیش می‌ره. پیشنهاد می‌دم یه چک‌این کوتاهِ روزانه بذاریم تا خیالتون راحت‌تر باشه و رفت‌وبرگشت کمتر شه.",
        why="نیازِ پشتِ کنترل (اطمینان) را می‌بیند؛ به‌جای دلخوری، راه‌حلِ ساختاری پیشنهاد می‌کند؛ حرفه‌ای و رو به جلو.",
    ),
    GoldenExample(
        id="mgr_unrealistic_deadline",
        relationship_type="manager_colleague",
        situation="ضرب‌الاجلِ غیرواقعی",
        user_goal="professional_reply",
        incoming="این پروژه باید تا آخر امروز کامل تحویل داده شه.",
        reply="اولویتش رو می‌فهمم و شروع می‌کنم. بخشِ اصلی تا آخرِ امروز آماده می‌شه؛ بخشِ [فلان] برای کیفیت به صبحِ فردا نیاز داره. اگر بخوای می‌تونم نسخه‌ی اولیه رو امروز بدم.",
        why="تعهد را نشان می‌دهد بدونِ قولِ توخالی؛ واقعیتِ زمان را شفاف می‌گوید؛ گزینه‌ی عملی روی میز می‌گذارد.",
    ),
    # --- calm_conflict ---
    GoldenExample(
        id="manager_calm_public_blame",
        relationship_type="manager_colleague",
        situation="سرزنش مدیر بابت اشتباه در جلسه",
        user_goal="calm_conflict",
        incoming="این اشتباه توی جلسه اعتبار تیم رو زیر سؤال برد.",
        reply="حق دارید ناراحت باشید؛ مسئولیت اون بخش با من بود. تا پایان امروز نسخه‌ی اصلاح‌شده را می‌فرستم و یک چک‌لیست بازبینی می‌گذارم که تکرار نشود.",
        why="Owns the mistake without self-flagellation; pivots immediately to a time-bound fix plus a systemic prevention step.",
    ),
    GoldenExample(
        id="colleague_calm_credit_dispute",
        relationship_type="manager_colleague",
        situation="عصبانیت همکار بابت برداشت از سهم کاری",
        user_goal="calm_conflict",
        incoming="شما کار من رو به اسم خودتون ارائه کردید و این اصلاً حرفه‌ای نیست.",
        reply="ممنون که مستقیم گفتید؛ قصد من این نبود ولی برداشت شما را می‌فهمم. در جلسه‌ی فردا سهم شما را شفاف اعلام می‌کنم و از این به بعد اسامی را قبل از ارائه هماهنگ می‌کنیم.",
        why="Validates the perception without confessing intent it didn't have; offers a public, verifiable correction plus a process fix.",
    ),
    # --- understand_only (minimal safe fallback) ---
    GoldenExample(
        id="manager_understand_vague_pause",
        relationship_type="manager_colleague",
        situation="دستور مبهم مدیر برای متوقف کردن پروژه",
        user_goal="understand_only",
        incoming="فعلاً این پروژه را نگه دارید، بعداً صحبت می‌کنیم.",
        reply="حتماً، متوقفش می‌کنم. فقط برای برنامه‌ریزی تیم، حدوداً چه زمانی فرصت گفت‌وگو دارید؟",
        why="Complies cleanly, then extracts the missing information (timeline) with a legitimate operational reason — no anxiety or pushback.",
    ),
    GoldenExample(
        id="manager_understand_cold_feedback",
        relationship_type="manager_colleague",
        situation="بازخورد سرد و کلی مدیر",
        user_goal="understand_only",
        incoming="خروجی این ماه اون چیزی نبود که انتظار داشتم.",
        reply="ممنون که گفتید. برای اینکه دقیق اصلاح کنم، ممکن است بفرمایید کدام بخش بیشترین فاصله را با انتظار شما داشت؟",
        why="Converts a vague criticism into specific, actionable data without defensiveness or emotional over-explaining.",
    ),
]


# ───────────────────────── customer ─────────────────────────
# Polite, service-oriented, solution-focused, represents the brand.
_CUSTOMER: list[GoldenExample] = [
    GoldenExample(
        id="cust_angry_delay",
        relationship_type="customer",
        situation="عصبانیتِ مشتری از تأخیر",
        user_goal="calm_conflict",
        incoming="سفارشم سه روز دیر شده، این چه وضعشه؟",
        reply="کاملاً حق دارید ناراحت باشید و عذرخواهی می‌کنم. همین الان وضعیتِ سفارشتون رو پیگیری می‌کنم و تا یک ساعتِ دیگه زمانِ دقیقِ تحویل رو بهتون اعلام می‌کنم.",
        why="نارضایتی را اعتبار می‌دهد و عذرخواهیِ حرفه‌ای می‌کند؛ بدونِ بحث، اقدامِ مشخص و زمان‌دار می‌دهد.",
    ),
    GoldenExample(
        id="cust_refund_request",
        relationship_type="customer",
        situation="درخواستِ بازگشتِ وجه",
        user_goal="professional_reply",
        incoming="پولمو پس می‌خوام، محصول خراب بود.",
        reply="بابتِ این تجربه متاسفم. حتماً پیگیری می‌کنم؛ لطفاً شماره‌ی سفارش رو بفرستید تا روندِ بازگشتِ وجه رو همین امروز شروع کنم.",
        why="مسئله را جدی می‌گیرد بدونِ دفاع؛ قدمِ عملیِ روشن می‌خواهد؛ زمانِ اقدام را مشخص می‌کند.",
    ),
    GoldenExample(
        id="cust_threat_bad_review",
        relationship_type="customer",
        situation="تهدید به نظرِ منفیِ عمومی",
        user_goal="calm_conflict",
        incoming="اگه درست نشه میرم همه جا نظر بد میذارم.",
        reply="نگرانیتون رو کاملاً درک می‌کنم و می‌خوام قبل از هر چیز مشکل حل بشه. اجازه بدید موضوع رو دقیق بررسی کنم و راه‌حل بهتون بدم.",
        why="تهدید را به نیازِ واقعی (حلِ مشکل) برمی‌گرداند؛ بدونِ ترس یا مقابله؛ تمرکز را روی راه‌حل می‌برد.",
    ),
    GoldenExample(
        id="cust_accusation_fraud",
        relationship_type="customer",
        situation="اتهامِ کلاهبرداری",
        user_goal="set_boundary",
        incoming="شما کلاهبردارید، پولمو خوردید.",
        reply="می‌فهمم که الان عصبانی هستید و می‌خوام کمک کنم. تراکنشِ شما قابلِ پیگیریه؛ شماره‌ی پیگیری رو بدید تا دقیق بررسی و شفاف اطلاع بدم.",
        why="عصبانیت را می‌پذیرد بدونِ تأییدِ اتهام؛ با شفافیت و مدرک مرزِ حرفه‌ای می‌گذارد؛ راهِ حل را باز می‌کند.",
    ),
    GoldenExample(
        id="cust_simple_followup",
        relationship_type="customer",
        situation="پیگیریِ سادهٔ وضعیتِ سفارش",
        user_goal="professional_reply",
        incoming="سفارشم کی می‌رسه؟",
        reply="ممنون از پیگیریتون. سفارشِ شما در حالِ ارساله و طبقِ برآورد تا فردا عصر دستتون می‌رسه؛ کدِ رهگیری رو هم خدمتتون می‌فرستم.",
        why="پاسخِ روشن و خدمت‌محور؛ اطلاعاتِ دقیق و قدمِ بعدی؛ کوتاه و مودبانه.",
    ),
    GoldenExample(
        id="cust_unreasonable_demand",
        relationship_type="customer",
        situation="درخواستِ خارج از سیاستِ شرکت",
        user_goal="set_boundary",
        incoming="باید همین الان رایگان برام بفرستید وگرنه شکایت می‌کنم.",
        reply="دوست دارم تا جای ممکن کمکتون کنم. ارسالِ رایگان خارج از سیاستِ ماست، اما می‌تونم در سریع‌ترین زمان با تخفیفِ ارسال موضوع رو براتون حل کنم.",
        why="تمایل به کمک را نشان می‌دهد؛ مرزِ سیاست را محترمانه اما قاطع می‌گذارد؛ جایگزینِ واقعی پیشنهاد می‌کند.",
    ),
    # --- calm_conflict ---
    GoldenExample(
        id="customer_calm_delayed_order",
        relationship_type="customer",
        situation="عصبانیت مشتری از تأخیر و بی‌پاسخی",
        user_goal="calm_conflict",
        incoming="این چه وضعشه؟ دو هفته‌ست پیگیرم و هیچ جوابی نمی‌گیرم!",
        reply="بابتِ این تأخیر و بی‌پاسخی عذرخواهی می‌کنم؛ این قابل قبول نیست. همین الان سفارشتون رو شخصاً پیگیری می‌کنم و تا ساعت ۱۷ امروز وضعیت دقیق را اطلاع می‌دهم.",
        why="Leads with ownership and honest admission ('unacceptable') instead of formulaic validation; gives a personal commitment with a specific deadline.",
    ),
    GoldenExample(
        id="customer_calm_refund_threat",
        relationship_type="customer",
        situation="تهدید مشتری به شکایت و پس گرفتن پول",
        user_goal="calm_conflict",
        incoming="یا همین امروز پولم رو برمی‌گردونید یا شکایت می‌کنم.",
        reply="ناراحتی شما کاملاً قابل درک است. درخواست بازگشت وجه را همین حالا ثبت می‌کنم؛ طبق رویه تا ۴۸ ساعت کاری به حساب شما برمی‌گردد و شماره‌ی پیگیری را برایتان ارسال می‌کنم.",
        why="De-escalates the threat by simply granting the legitimate request with a concrete timeline and tracking — removes the need for conflict.",
    ),
]


# ───────────────────────── family ─────────────────────────
# Respectful, calm, preserves independence; soft but impenetrable boundaries.
_FAMILY: list[GoldenExample] = [
    GoldenExample(
        id="fam_marriage_pressure",
        relationship_type="family",
        situation="فشار برای ازدواج",
        user_goal="set_boundary",
        incoming="کی می‌خوای سر و سامون بگیری؟ آبرومون رفت.",
        reply="می‌دونم نگرانمی و از سرِ دلسوزیه. این تصمیمِ خودمه و سرِ وقتش انجامش می‌دم؛ بیا انرژیمونو صرفِ چیزای قشنگ‌تر کنیم.",
        why="دلسوزی را به رسمیت می‌شناسد؛ مالکیتِ تصمیم را نرم اما قاطع می‌گیرد؛ بحث را به فضای گرم‌تر می‌برد.",
    ),
    GoldenExample(
        id="fam_guilt_no_visit",
        relationship_type="family",
        situation="گله از کم‌رفت‌وآمد",
        user_goal="calm_conflict",
        incoming="دیگه اصلا بهمون سر نمی‌زنی، انگار غریبه شدیم.",
        reply="دلم براتون تنگ شده، راست می‌گید این مدت کم بودم. آخرِ همین هفته میام پیشتون، قول.",
        why="گله را بدونِ دفاع می‌پذیرد؛ سهمِ خودش را می‌گیرد؛ قدمِ مشخص و گرم می‌دهد، نه وعده‌ی کلی.",
    ),
    GoldenExample(
        id="fam_money_request",
        relationship_type="family",
        situation="درخواستِ کمکِ مالی با فشار",
        user_goal="set_boundary",
        incoming="یه مبلغ لازم دارم، می‌دونم که برات کاری نداره.",
        reply="هر کاری از دستم بربیاد برات می‌کنم. الان شرایطم اون‌طور که فکر می‌کنی نیست؛ بذار ببینم چقدر می‌تونم کمک کنم و راستشو بهت می‌گم.",
        why="محبت را نشان می‌دهد بدونِ بله‌ی تحتِ فشار؛ واقعیتِ شرایط را شفاف می‌گوید؛ یک قدمِ صادقانه می‌گذارد.",
    ),
    GoldenExample(
        id="fam_comparison",
        relationship_type="family",
        situation="مقایسه با دیگران",
        user_goal="calm_conflict",
        incoming="پسر فلانی هم سنِ توئه، ببین به کجا رسیده.",
        reply="می‌دونم آرزوهای خوبی برام دارید. من راهِ خودمو دارم و دارم تلاشمو می‌کنم؛ دوست دارم شما هم بهم ایمان داشته باشید.",
        why="نیتِ خوب را می‌بیند بدونِ پذیرشِ مقایسه؛ مسیرِ خودش را با احترام تثبیت می‌کند؛ نیازِ واقعی (اعتماد) را می‌گوید.",
    ),
    GoldenExample(
        id="fam_interfering_parenting",
        relationship_type="family",
        situation="دخالت در شیوه‌ی فرزندپروری",
        user_goal="set_boundary",
        incoming="چرا بچه‌تو این‌جوری بزرگ می‌کنی؟ ما این‌جوری بزرگت نکردیم.",
        reply="ممنون که به فکرشید. ما هم داریم تلاشِ خودمونو می‌کنیم و یه‌سری چیزا رو جورِ دیگه پیش می‌بریم؛ نگران نباشید، حواسمون هست.",
        why="نگرانی را محترمانه می‌پذیرد؛ مرزِ تصمیمِ خانوادگیِ خودش را بدونِ تقابل می‌گذارد؛ بحثِ عقیدتیِ طولانی را باز نمی‌کند.",
    ),
    GoldenExample(
        id="fam_emotional_blackmail",
        relationship_type="family",
        situation="باج‌گیریِ عاطفی",
        user_goal="set_boundary",
        incoming="اگه این کارو بکنی دیگه منو نمی‌بینی.",
        reply="دوستت دارم و نمی‌خوام ناراحت شی. ولی این تصمیم برام مهمه و امیدوارم با وجودِ اختلافمون کنارِ هم بمونیم.",
        why="محبت را جدا از تسلیم می‌گذارد؛ زیرِ بارِ تهدیدِ عاطفی نمی‌رود؛ درِ رابطه را باز نگه می‌دارد.",
    ),
    GoldenExample(
        id="fam_sibling_unseen",
        relationship_type="family",
        situation="حسِ نادیده‌گرفته‌شدن توسط خواهر/برادر",
        user_goal="calm_conflict",
        incoming="تو همیشه طرفِ اونی، من تو این خونه هیچی نیستم.",
        reply="اصلا دوست ندارم همچین حسی داشته باشی. جایگاهِ تو برام مهمه؛ بگو کجا حس کردی نادیده‌ت گرفتم تا درستش کنیم.",
        why="حس را آرام می‌کند بدونِ تأییدِ کلیِ اتهام؛ ارزشِ طرف را می‌گوید؛ مشخص می‌پرسد، نه کلی.",
    ),
    GoldenExample(
        id="fam_drifted_apart",
        relationship_type="family",
        situation="فاصله‌ی عاطفی و دلتنگی",
        user_goal="improve_relationship",
        incoming="دیگه مثلِ قدیم با هم حرف نمی‌زنیم.",
        reply="راست می‌گی، دلم برای حرفامون تنگ شده. این هفته یه روز بریم بیرون فقط خودمون دوتا، باشه؟",
        why="فاصله را صادقانه می‌پذیرد؛ دلتنگی را می‌گوید؛ قدمِ مشخص و گرم برای ترمیم پیشنهاد می‌کند.",
    ),
    # --- make_them_accountable ---
    GoldenExample(
        id="family_accountable_sibling_noshow",
        relationship_type="family",
        situation="نیومدن خواهر/برادر سر قرار بیمارستان مادر",
        user_goal="make_them_accountable",
        incoming="نشد بیام دیگه، تو که بودی.",
        reply="آره بودم، ولی قرارمون این بود که با هم باشیم. دفعه‌ی بعد یا بیا، یا از قبل بگو که بدونم همه‌چی گردن منه.",
        why="Names the broken agreement, not the person's character; gives two concrete acceptable behaviors instead of guilt.",
    ),
    GoldenExample(
        id="family_accountable_broken_promise",
        relationship_type="family",
        situation="زیر قول زدن عضو خانواده و عادی‌سازی آن",
        user_goal="make_them_accountable",
        incoming="حالا مگه چی شده؟ خانواده‌ایم دیگه، این حرفا رو نداریم.",
        reply="اتفاقاً چون خانواده‌ایم برام مهمه. قول داده بودی و انجام نشد؛ فقط بگو کی انجامش می‌دی که دیگه پیگیری نکنم.",
        why="Flips the 'we're family' deflection into the reason the standard matters; ends with a dated commitment request, not a lecture.",
    ),
    # --- improve_relationship ---
    GoldenExample(
        id="family_improve_parent_softstep",
        relationship_type="family",
        situation="گام نرم پدر/مادر بعد از مدت‌ها سردی",
        user_goal="improve_relationship",
        incoming="دیروز غذای موردعلاقه‌تو درست کردم، یادت بود؟",
        reply="آره که یادمه، هیچ‌جا اون مزه نمیشه. این هفته یه شب میام پیشتون، دور هم باشیم.",
        why="Catches the parent's indirect peace offering (food = love language) and answers it with presence, not words.",
    ),
    GoldenExample(
        id="family_improve_distant_sibling",
        relationship_type="family",
        situation="گلایه‌ی ملایم خواهر/برادر از کم‌رنگ شدن رابطه",
        user_goal="improve_relationship",
        incoming="دیگه اصلاً از هم خبر نداریم. یادته قبلاً چقدر با هم بودیم؟",
        reply="آره، و راستش خودمم دلم برای اون موقع‌ها تنگ شده. بیا از همین هفته یه کار ثابت بذاریم، حتی یه تماس کوتاه آخر هفته‌ها.",
        why="Matches the vulnerability instead of explaining the distance; converts nostalgia into one small sustainable ritual.",
    ),
]


# ───────────────────────── friend ─────────────────────────
# Intimate, equal, supportive — without becoming the savior or a pushover.
_FRIEND: list[GoldenExample] = [
    GoldenExample(
        id="friend_canceled_again",
        relationship_type="friend",
        situation="گله از کنسل‌کردنِ قرار",
        user_goal="calm_conflict",
        incoming="بازم قرارو پیچوندی، رفیق به این می‌گن؟",
        reply="حق داری دلخور شی، بدقولی کردم. این هفته جبران می‌کنم، کجا بریم که حال کنیم؟",
        why="بدقولی را بدونِ بهانه می‌پذیرد؛ سهم می‌گیرد؛ جبرانِ مشخص و صمیمی پیشنهاد می‌کند.",
    ),
    GoldenExample(
        id="friend_owes_money",
        relationship_type="friend",
        situation="پس‌گرفتنِ قرض از دوست",
        user_goal="make_them_accountable",
        incoming="پولو یادم میمونه بهت بدم بابا، چقدر گیر میدی.",
        reply="می‌دونم یادت می‌مونه، فقط چون خودمم لازمش دارم گفتم. آخرِ هفته اوکیه؟",
        why="بدونِ سرزنش، دلیلِ پیگیری را شفاف می‌گوید؛ زمانِ مشخص می‌خواهد؛ رفاقت را نمی‌سوزاند.",
    ),
    GoldenExample(
        id="friend_emotional_demand",
        relationship_type="friend",
        situation="درخواستِ حضورِ فوری در بحران",
        user_goal="set_boundary",
        incoming="باید الان بیای پیشم، حالم اصلا خوب نیست.",
        reply="نگرانت شدم رفیق. الان نمی‌تونم بیام ولی پای تلفن کاملاً هستم؛ بگو چی شده.",
        why="نگرانیِ واقعی نشان می‌دهد؛ مرزِ توانِ خودش را صادقانه می‌گذارد؛ حمایتِ ممکن را جایگزین می‌کند.",
    ),
    GoldenExample(
        id="friend_jealous_distance",
        relationship_type="friend",
        situation="گله از کم‌رنگ‌شدنِ رفاقت",
        user_goal="calm_conflict",
        incoming="تازگیا فقط با اون می‌پری، ما رو فراموش کردی.",
        reply="اصلا این‌طور نیست، تو همیشه رفیقِ فابریکمی. راست می‌گی کم بودم، بیا این هفته بترکونیم.",
        why="نگرانی را با اطمینان جواب می‌دهد؛ سهمِ کم‌بودن را می‌گیرد؛ قدمِ گرم و مشخص می‌گذارد.",
    ),
    GoldenExample(
        id="friend_flaky_plan",
        relationship_type="friend",
        situation="بی‌برنامگیِ طرف برای قرار",
        user_goal="set_boundary",
        incoming="نمیدونم بیام یا نه، شاید، ببینم چی میشه.",
        reply="اوکی ولی من باید برنامه‌مو بچینم. تا فردا ظهر قطعی بگو که بدونم رومی حساب کنم یا نه.",
        why="انعطاف را تا حدی می‌پذیرد؛ نیازِ خودش به قطعیت را روشن می‌گوید؛ مرزِ زمانیِ منصفانه می‌گذارد.",
    ),
    # --- avoid_needy ---
    GoldenExample(
        id="friend_avoid_needy_late_apology",
        relationship_type="friend",
        situation="عذرخواهی دیرهنگام دوست بابت بی‌خبری",
        user_goal="avoid_needy",
        incoming="ببخشید جواب ندادم، این هفته خیلی داغونم.",
        reply="فدای سرت، اصلاً فکرشم نکن. هر وقت حالت جا اومد خبر بده، یه قهوه ازت طلب دارم.",
        why="Zero guilt-tripping, zero interrogation; keeps warmth and a light future hook without pressure.",
    ),
    GoldenExample(
        id="friend_avoid_needy_cancelled_plan",
        relationship_type="friend",
        situation="کنسل کردن قرار توسط دوست",
        user_goal="avoid_needy",
        incoming="این هفته نمی‌تونم بیام، برنامه‌م به‌هم ریخته.",
        reply="اوکیه، اصلاً نگرانش نباش. هفته‌ی بعد یه روز بگو که جفتمون اوکی باشیم.",
        why="Accepts gracefully and hands the next move back to the friend — the opposite of chasing.",
    ),
    GoldenExample(
        id="friend_avoid_needy_too_many_messages",
        relationship_type="friend",
        situation="گلایه‌ی دوست از پیام زیاد",
        user_goal="avoid_needy",
        incoming="چرا انقدر پیام میدی؟ یه کم سرم شلوغه.",
        reply="باشه، راحت باش. هر وقت سرت خلوت شد خودت بیا.",
        why="No defense, no over-apology, no counter-attack; pulls back cleanly and restores symmetry in one move.",
    ),
    # --- make_them_accountable ---
    GoldenExample(
        id="friend_accountable_repeated_flaking",
        relationship_type="friend",
        situation="کوچیک‌شماری پیچوندن قرار تکراری",
        user_goal="make_them_accountable",
        incoming="ای بابا، حالا یه قرارو پیچوندم، چرا انقدر بزرگش می‌کنی؟",
        reply="بحث یه قرار نیست، این چند ماه چند بار تکرار شده. من برات وقت می‌ذارم و همینو ازت می‌خوام. اگه برات سخته، از اول بگو که برنامه نچینم.",
        why="Reframes from incident to pattern without name-calling; states the standard and offers an honest exit instead of an ultimatum.",
    ),
    GoldenExample(
        id="friend_accountable_unreturned_loan",
        relationship_type="friend",
        situation="تعویق مبهم در پس دادن قرض",
        user_goal="make_them_accountable",
        incoming="حواسم نبود، حالا بعداً بهت میدم.",
        reply="می‌دونم قصدی نداری، ولی سه هفته گذشته و منم حسابش روش بود. یه تاریخ مشخص بگو که خیال جفتمون راحت شه.",
        why="Assumes good intent explicitly, then converts vague 'later' into a concrete commitment — accountability without accusation.",
    ),
]


GOLDEN_EXAMPLES: list[GoldenExample] = [
    *_ROMANTIC,
    *_EX,
    *_MANAGER,
    *_CUSTOMER,
    *_FAMILY,
    *_FRIEND,
]


def select_golden_examples(
    relationship_type: str,
    user_goal: str,
    limit: int = 4,
) -> list[GoldenExample]:
    """Return the most relevant golden examples for the given (relationship, goal).

    Selection scopes to the message's ``relationship_type`` first. Within that
    pool, examples whose ``user_goal`` matches are preferred, then the rest of
    the pool fills up to ``limit`` so the model always sees a few exemplars of
    the target tone. Relationship types with no curated examples return an empty
    list, leaving the generic path unaffected.
    """
    pool = [ex for ex in GOLDEN_EXAMPLES if ex.relationship_type == relationship_type]
    if not pool:
        return []
    matching = [ex for ex in pool if ex.user_goal == user_goal]
    others = [ex for ex in pool if ex.user_goal != user_goal]
    return (matching + others)[: max(0, limit)]


def golden_examples_for_prompt(
    relationship_type: str,
    user_goal: str,
    limit: int = 4,
) -> list[dict[str, str]]:
    """Compact (incoming -> ideal_reply) pairs ready to embed in the prompt.

    Used when few-shot conversation turns are disabled; otherwise see
    ``golden_examples_as_messages``.
    """
    return [
        {"پیام_دریافتی": ex.incoming, "جوابِ_طلایی": ex.reply}
        for ex in select_golden_examples(relationship_type, user_goal, limit)
    ]


def golden_examples_as_messages(
    relationship_type: str,
    user_goal: str,
    limit: int = 4,
) -> list[dict[str, str]]:
    """Golden examples as real few-shot conversation turns (user/assistant pairs).

    Each example becomes a (user -> assistant) turn where the user message
    presents the incoming text and the assistant message gives the ideal reply,
    both as compact JSON to keep the json-in/json-out contract consistent with
    the real task. Models imitate tone/structure far better from genuine turns
    than from a list buried inside the task payload.
    """
    import json

    messages: list[dict[str, str]] = []
    for ex in select_golden_examples(relationship_type, user_goal, limit):
        messages.append({
            "role": "user",
            "content": json.dumps(
                {"task": "style_reference", "پیام_دریافتی": ex.incoming},
                ensure_ascii=False,
            ),
        })
        messages.append({
            "role": "assistant",
            "content": json.dumps({"جوابِ_طلایی": ex.reply}, ensure_ascii=False),
        })
    return messages
