"use client";

import {
  AlertCircle,
  Check,
  Clock,
  Copy,
  Heart,
  Lock,
  LogIn,
  MessageCircle,
  Search,
  ShieldAlert,
  ShieldCheck,
  Sparkles,
  User,
  Zap
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { notifyTelegramOtp, requestOtp, verifyOtp } from "../lib/api";
import { faNum } from "../lib/format";

const valueProps = [
  { icon: Zap, title: "در چند ثانیه، نه ساعت‌ها کلنجار", text: "به‌جای ده‌بار خواندنِ یک پیام و حدس‌زدن، سریع به یک برداشتِ روشن می‌رسی." },
  { icon: ShieldAlert, title: "قبل از فرستادن، ریسک را ببین", text: "می‌فهمی کجای جوابت ممکن است بد برداشت شود و کجا رابطه را سرد می‌کند." },
  { icon: Heart, title: "یک پاسخِ آرام‌تر، آماده", text: "یک نسخهٔ متعادل که همان را بفرستی، یا دلخواهت را از رویش بسازی." }
];

const steps = [
  { n: "۱", title: "پیام را بگذار", text: "متنی که گرفته‌ای را کپی کن و بچسبان — همین. اگر خواستی، می‌توانی کلِ ماجرا را هم تعریف کنی." },
  { n: "۲", title: "برداشتِ پشتش را ببین", text: "پیام از سه لنزِ روان‌شناختی خوانده می‌شود تا بفهمی واقعاً دنبالِ چیست، نه فقط چه گفته." },
  { n: "۳", title: "با خیال راحت جواب بده", text: "یک پاسخِ آرام و آماده می‌گیری؛ همان را بفرست یا لحنش را به دلخواه تنظیم کن." }
];

const lenses = [
  { lc: "var(--dopamine)", title: "هدف و کنترل", role: "دوپامین", text: "دنبالِ چیست و کجا کوتاه می‌آید؟ این لنز نشان می‌دهد طرف چه می‌خواهد و چه چیزی برایش بُرد حساب می‌شود." },
  { lc: "var(--oxytocin)", title: "امنیت و اعتماد", role: "اکسی‌توسین", text: "می‌خواهد مطمئن شود هنوز کنارش هستی. خیلی از پیام‌های تند، در اصل دنبالِ یک اطمینان‌اند." },
  { lc: "var(--serotonin)", title: "شأن و احترام", role: "سروتونین", text: "حواسش به دیده‌شدن و جایگاهش است. وقتی احساسِ کم‌اهمیت‌شدن کند، لحن عوض می‌شود." }
];

const feats = [
  { title: "گفت‌وگوی منتهی به پیام", text: "چند پیامِ آخر را بده تا ترتیب و لحنِ ماجرا روشن شود." },
  { title: "پیشینه و رفتارِ طرف", text: "قبلش چه شد و این اواخر چطور بوده؟ تحلیل عمیق‌تر می‌شود." },
  { title: "قوسِ ماجرا و مسیرِ پیش‌رو", text: "می‌بینی کجا اوضاع چرخید و اگر همین‌طور پیش برود، به کجا می‌رسد." }
];

const quotes = [
  { av: "ن", text: "سه بار جلوی فرستادنِ یک پیامِ عصبانی را گرفت. همین یک‌بار هم ارزشش را داشت.", nm: "نگار", rl: "کاربرِ تلگرام" },
  { av: "س", text: "همیشه فکر می‌کردم طرف از دستم عصبانیه؛ فهمیدم فقط دنبالِ یک اطمینان بوده.", nm: "سامان", rl: "رابطهٔ دوستی" },
  { av: "م", text: "پاسخی که پیشنهاد داد دقیقاً همان چیزی بود که می‌خواستم بگویم ولی بلد نبودم.", nm: "مریم", rl: "رابطهٔ عاطفی" }
];

export default function Home() {
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [credits, setCredits] = useState(0);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [scrolled, setScrolled] = useState(false);
  const modalRef = useRef<HTMLDivElement>(null);

  // nav shadow on scroll
  useEffect(() => {
    const onScroll = () => setScrolled(window.scrollY > 12);
    onScroll();
    window.addEventListener("scroll", onScroll, { passive: true });
    return () => window.removeEventListener("scroll", onScroll);
  }, []);

  // reveal-on-scroll
  useEffect(() => {
    const els = Array.from(document.querySelectorAll<HTMLElement>(".web-landing .reveal"));
    if (!("IntersectionObserver" in window)) {
      els.forEach((el) => el.classList.add("in"));
      return;
    }
    const io = new IntersectionObserver(
      (entries) => {
        entries.forEach((e) => {
          if (e.isIntersecting) {
            e.target.classList.add("in");
            io.unobserve(e.target);
          }
        });
      },
      { threshold: 0.14, rootMargin: "0px 0px -40px 0px" }
    );
    els.forEach((el) => io.observe(el));
    return () => io.disconnect();
  }, []);

  // focus trap for auth modal
  useEffect(() => {
    if (!authModalOpen) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const focusables = () =>
      Array.from(
        modalRef.current?.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), textarea:not([disabled])'
        ) ?? []
      );
    focusables()[0]?.focus();
    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") return setAuthModalOpen(false);
      if (event.key !== "Tab") return;
      const items = focusables();
      if (!items.length) return;
      const first = items[0];
      const last = items[items.length - 1];
      if (event.shiftKey && document.activeElement === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && document.activeElement === last) {
        event.preventDefault();
        first.focus();
      }
    }
    window.addEventListener("keydown", onKey);
    return () => {
      window.removeEventListener("keydown", onKey);
      previouslyFocused?.focus();
    };
  }, [authModalOpen]);

  async function handleOtp() {
    if (!phone.trim()) {
      setError("برای ساخت حساب و دریافت کد ورود، شماره موبایل را وارد کنید.");
      return;
    }
    setError("");
    setStatus("داریم کد ورود را می‌فرستیم...");
    try {
      const result = await requestOtp(phone);
      await notifyTelegramOtp(result.telegram_payload);
      setOtpSent(true);
      setStatus("کد ورود ارسال شد. اگر تلگرام را وصل کرده باشید، کد ورود می‌تواند از همان‌جا هم به دستتان برسد.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "کد ورود ارسال نشد. دوباره تلاش کنید.");
      setStatus("");
    }
  }

  async function handleVerify() {
    if (!otp.trim()) {
      setError("کد ورود را وارد کنید.");
      return;
    }
    setError("");
    setStatus("داریم کد را بررسی می‌کنیم...");
    try {
      const result = await verifyOtp(phone, otp);
      setCredits(result.credit_balance);
      window.localStorage.setItem("message-decoder-token", result.token);
      window.localStorage.setItem("message-decoder-phone", phone);
      setStatus("اعتبار فعال شد؛ حالا می‌توانید پاسخ کامل بسازید.");
      window.setTimeout(() => window.location.assign("/decoder"), 700);
    } catch (err) {
      setError(err instanceof Error ? err.message : "این کد درست نیست یا منقضی شده است.");
      setStatus("");
    }
  }

  return (
    <div className="web-landing">
      {/* ===== NAV ===== */}
      <header className={`nav ${scrolled ? "scrolled" : ""}`} id="nav">
        <div className="wrap nav-in">
          <a className="brand" href="#top">
            <span className="logo">
              <Search size={20} strokeWidth={2} />
            </span>
            Message Decoder
          </a>
          <nav className="nav-links">
            <a href="#how">چطور کار می‌کند</a>
            <a href="#lenses">سه لنز</a>
            <a href="#episode">تحلیلِ موقعیت</a>
          </nav>
          <div className="nav-cta">
            {credits > 0 && (
              <span className="eyebrow" style={{ padding: "7px 13px" }}>
                <Sparkles size={14} /> {faNum(credits)} اعتبار
              </span>
            )}
            <button className="btn btn-ghost btn-sm" onClick={() => setAuthModalOpen(true)}>ورود</button>
            <Link className="btn btn-primary btn-sm" href="/onboarding">شروعِ رایگان</Link>
          </div>
        </div>
      </header>

      {/* ===== HERO ===== */}
      <section className="hero" id="top">
        <div className="aurora-bg"><span className="blob b1" /><span className="blob b2" /></div>
        <div className="wrap hero-grid">
          <div className="hero-copy">
            <span className="eyebrow"><span className="dot" /> رایگان برای اولین پیام · بدون ثبت‌نام</span>
            <h1 className="hero-h">اون پیام دقیقاً یعنی چی، و <em>چی</em> جواب بدم؟</h1>
            <p className="hero-sub">پیامِ سرد، متلک یا سکوتِ سنگین می‌گیری و ذهنت قفل می‌کند. متن را بگذار تا در چند ثانیه برداشتِ واقعیِ پشتش، ریسکِ سوءتفاهم و یک پاسخِ آرام و آماده را ببینی.</p>
            <div className="hero-actions">
              <Link className="btn btn-primary btn-lg" href="/onboarding"><Sparkles size={19} /> همین حالا یک پیام را رمزگشایی کن</Link>
              <a className="btn btn-ghost btn-lg" href="#how">چطور کار می‌کند؟</a>
            </div>
            <div className="hero-trust">
              <span><Clock size={16} /> نتیجه در چند ثانیه</span>
              <span><Lock size={16} /> خصوصی و امن</span>
              <span><MessageCircle size={16} /> وب و تلگرام</span>
            </div>
          </div>

          <div className="demo">
            <span className="demo-tag">یک نمونهٔ واقعی</span>
            <div className="in-bubble">
              <div className="meta"><User size={14} /> طرف مقابل · بعد از کنسل‌شدنِ قرار</div>
              نه بابا، مهم نیست. باشه یه وقت دیگه. می‌دونم سرت شلوغه.
            </div>
            <div className="demo-flow"><Sparkles size={15} /> تحلیل در چند ثانیه</div>
            <span className="lens-chip"><span className="gl" /> امنیت و اعتماد</span>
            <p className="demo-read">ظاهرش بزرگواری و درک‌کردن است، ولی «یه وقت دیگه» یک آزمونِ نرم است: منتظر است تو پیش‌قدم شوی و نشان دهی هنوز برایت در اولویت است.</p>
            <div className="reply">
              <div className="reply-meta">
                <span className="t"><Heart size={15} /> پاسخِ پیشنهادی</span>
                <span className="c"><Copy size={14} /> کپی</span>
              </div>
              <p>راست می‌گی، چند بار عقب افتاد و این درست نیست. بیا همین الان یه روزِ قطعی بذاریم که این‌بار حتماً بشه — پنجشنبه عصر خوبه برات؟</p>
            </div>
          </div>
        </div>
      </section>

      {/* ===== VALUE PROPS ===== */}
      <section className="band band-alt" id="value">
        <div className="wrap">
          <div className="sec-head reveal">
            <span className="kicker">چرا Message Decoder</span>
            <h2 className="sec-h">قبل از فرستادن، نه بعد از پشیمانی</h2>
            <p className="sec-sub">یک پیامِ عجولانه می‌تواند چند هفته رابطه را سرد کند. این ابزار همان چند ثانیهٔ مکث را به تو می‌دهد.</p>
          </div>
          <div className="vp-grid">
            {valueProps.map((v) => {
              const Icon = v.icon;
              return (
                <div className="vp reveal" key={v.title}>
                  <span className="ic"><Icon size={25} /></span>
                  <h3>{v.title}</h3>
                  <p>{v.text}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      {/* ===== HOW IT WORKS ===== */}
      <section className="band" id="how">
        <div className="wrap">
          <div className="sec-head reveal">
            <span className="kicker">سه قدمِ ساده</span>
            <h2 className="sec-h">چطور کار می‌کند</h2>
          </div>
          <div className="steps">
            {steps.map((s) => (
              <div className="step reveal" key={s.n}>
                <span className="num">{s.n}</span>
                <h3>{s.title}</h3>
                <p>{s.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== THREE LENSES ===== */}
      <section className="band band-alt" id="lenses">
        <div className="wrap">
          <div className="sec-head reveal">
            <span className="kicker">روشِ ما</span>
            <h2 className="sec-h">هر پیام را از سه لنز می‌بینیم</h2>
            <p className="sec-sub">آدم‌ها از سه جای متفاوت پیام می‌دهند. ما هر سه را می‌سنجیم تا تو مجبور به حدس‌زدن نباشی.</p>
          </div>
          <div className="lens-grid">
            {lenses.map((l) => (
              <div className="lens-card reveal" key={l.role} style={{ ["--lc" as string]: l.lc }}>
                <span className="orb" />
                <h3>{l.title}</h3>
                <div className="role">{l.role}</div>
                <p>{l.text}</p>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== EPISODE / SITUATION ===== */}
      <section className="band" id="episode">
        <div className="wrap split">
          <div className="split-media reveal">
            <div className="thread">
              <div className="tmsg them"><span className="who">او</span>ببخشید دیشب درگیر بودم 🙏</div>
              <div className="tmsg me"><span className="who">من</span>اشکالی نداره، ولی حس می‌کنم دیگه اولویتت نیستم.</div>
              <div className="tmsg them"><span className="who">او</span>باز شروع شد...</div>
            </div>
            <div className="arc">
              <div className="arc-row"><span className="arc-dot" /><div><div className="arc-when">شروع</div><div className="arc-what">یک قرارِ تماس فراموش شد — یک لغزشِ کوچک.</div></div></div>
              <div className="arc-row"><span className="arc-dot" /><div><div className="arc-when">بعدش</div><div className="arc-what">تو دلخوری‌ات را گفتی؛ او دفاع کرد، نه دلجویی.</div></div></div>
              <div className="arc-row"><span className="arc-dot" /><div><div className="arc-when">حالا</div><div className="arc-what">بحث رسیده به «من برات مهم نیستم».</div></div></div>
            </div>
          </div>
          <div className="split-copy reveal">
            <span className="kicker">فراتر از یک پیام</span>
            <h2 className="sec-h">یک پیام، وسطِ یک ماجراست</h2>
            <p className="sec-sub">کاربرها معمولاً یک اتفاق را تعریف می‌کنند: فلانی آمد، این کار را کرد، من این حس را داشتم. Message Decoder کلِ آن موقعیت را می‌بیند — نه فقط آخرین خط.</p>
            <div className="feat-list">
              {feats.map((f) => (
                <div className="feat-item" key={f.title}>
                  <span className="ck"><Check size={16} strokeWidth={2.4} /></span>
                  <div><h4>{f.title}</h4><p>{f.text}</p></div>
                </div>
              ))}
            </div>
            <Link className="btn btn-primary" href="/onboarding" style={{ marginTop: 30 }}><Sparkles size={19} /> موقعیتت را تحلیل کن</Link>
          </div>
        </div>
      </section>

      {/* ===== TESTIMONIALS ===== */}
      <section className="band band-alt">
        <div className="wrap">
          <div className="sec-head reveal">
            <span className="kicker">حرفِ کاربرها</span>
            <h2 className="sec-h">یک مکثِ کوتاه، فرقِ بزرگ</h2>
          </div>
          <div className="quotes">
            {quotes.map((q) => (
              <div className="quote reveal" key={q.nm}>
                <span className="mark">”</span>
                <p>{q.text}</p>
                <div className="by"><span className="av">{q.av}</span><div><div className="nm">{q.nm}</div><div className="rl">{q.rl}</div></div></div>
              </div>
            ))}
          </div>
        </div>
      </section>

      {/* ===== PRIVACY ===== */}
      <section className="band" style={{ paddingTop: 0 }}>
        <div className="wrap">
          <div className="privacy reveal">
            <span className="shield"><ShieldCheck size={28} /></span>
            <div>
              <h3>پیام‌هایت پیشِ خودت می‌ماند</h3>
              <p>خصوصی طراحی شده؛ متنت برای تبلیغات یا فروش استفاده نمی‌شود و هر زمان بخواهی پاک می‌شود.</p>
            </div>
          </div>
        </div>
      </section>

      {/* ===== FINAL CTA ===== */}
      <section className="band" id="start">
        <div className="wrap">
          <div className="final reveal">
            <h2>قبل از جواب دادن، یک نفس بکش.</h2>
            <p>اولین تحلیل رایگان است. یک پیام را امتحان کن و تفاوتش را ببین.</p>
            <Link className="btn btn-primary btn-lg" href="/onboarding"><Sparkles size={19} /> تحلیلِ رایگانِ اولین پیام</Link>
          </div>
        </div>
      </section>

      {/* ===== FOOTER ===== */}
      <footer className="foot">
        <div className="wrap foot-in">
          <div>
            <a className="brand" href="#top">
              <span className="logo"><Search size={20} strokeWidth={2} /></span>
              Message Decoder
            </a>
            <p className="foot-tag">قبل از جواب دادن، یک نفس بکش. پیام را بفهم، آرام جواب بده.</p>
          </div>
          <div className="foot-cols">
            <div className="foot-col">
              <h4>محصول</h4>
              <a href="#how">چطور کار می‌کند</a>
              <a href="#lenses">سه لنز</a>
              <a href="#episode">تحلیلِ موقعیت</a>
            </div>
            <div className="foot-col">
              <h4>دسترسی</h4>
              <Link href="/decoder">وب</Link>
              <a href="https://t.me/MeDecoderBot" target="_blank" rel="noreferrer">تلگرام</a>
            </div>
            <div className="foot-col">
              <h4>پشتیبانی</h4>
              <Link href="/dashboard">داشبورد</Link>
              <button type="button" onClick={() => setAuthModalOpen(true)}>ورود / اعتبار</button>
            </div>
          </div>
        </div>
        <div className="wrap foot-bottom">
          <span>© {faNum(1405)} Message Decoder — همهٔ حقوق محفوظ است.</span>
          <span>ساخته‌شده برای گفت‌وگوهای آرام‌تر</span>
        </div>
      </footer>

      {/* ===== AUTH MODAL (functional) ===== */}
      {authModalOpen && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label="ورود و دریافت اعتبار"
          onClick={() => setAuthModalOpen(false)}
        >
          <div className="auth-modal" ref={modalRef} onClick={(e) => e.stopPropagation()}>
            <button className="modal-close" onClick={() => setAuthModalOpen(false)} aria-label="بستن">×</button>
            <div className="auth-modal-header">
              <span>ورود و اعتبار</span>
              <h2>با شماره موبایل وارد شوید</h2>
              <p>برای تحلیل اولیه لازم نیست وارد شوید. برای پاسخ‌های قابل کپی، کد ورود را با SMS/OTP می‌گیرید؛ اگر حساب تلگرام همین شماره را داشته باشد، کد داخل تلگرام هم ارسال می‌شود.</p>
            </div>
            {status && <div className="toast-msg toast-success"><Check size={16} /><span>{status}</span></div>}
            {error && <div className="toast-msg toast-error"><AlertCircle size={16} /><span>{error}</span></div>}
            <div className="auth-grid">
              <div className="auth-row">
                <input type="tel" inputMode="tel" autoComplete="tel" placeholder="09123456789" value={phone} onChange={(e) => setPhone(e.target.value)} />
                <button className="btn-secondary" onClick={handleOtp}><LogIn size={15} /> گرفتن کد ورود</button>
              </div>
              {otpSent && (
                <div className="auth-row">
                  <input type="text" inputMode="numeric" autoComplete="one-time-code" placeholder="کد ورود" value={otp} onChange={(e) => setOtp(e.target.value)} />
                  <button className="btn-primary btn-compact" onClick={handleVerify}>ورود و فعال‌سازی اعتبار</button>
                </div>
              )}
            </div>
            <Link className="auth-free-link" href="/decoder" onClick={() => setAuthModalOpen(false)}>اول تحلیل رایگان را ببینم</Link>
          </div>
        </div>
      )}
    </div>
  );
}
