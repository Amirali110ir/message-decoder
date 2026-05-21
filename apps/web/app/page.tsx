"use client";

import {
  AlertCircle,
  Check,
  ClipboardCheck,
  Compass,
  MessageSquareText,
  LogIn,
  Quote,
  ShieldAlert,
  Sparkles,
  User
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import { requestOtp, verifyOtp } from "../lib/api";

const benefitCards = [
  {
    icon: ShieldAlert,
    title: "کم‌کردن سوءتفاهم قبل از پاسخ",
    text: "پیام‌های سرد یا کنایه‌آمیز را فقط از روی کلمات قضاوت نکنید. قبل از دفاع کردن، نیاز احتمالی پشت واکنش را ببینید."
  },
  {
    icon: Compass,
    title: "وضوح بیشتر در پیام‌های مبهم",
    text: "وقتی شریک عاطفی، دوست یا مدیرتان مبهم حرف می‌زند، چند برداشت محتمل می‌بینید تا با عجله جواب ندهید."
  },
  {
    icon: ClipboardCheck,
    title: "پاسخ‌هایی که تنش را کمتر می‌کنند",
    text: "پاسخ نرم، قاطع، کوتاه یا پایان‌دهنده بسازید؛ طوری که حرفتان روشن بماند و رابطه بی‌دلیل آسیب نبیند."
  }
];

const lensCards = [
  {
    eyebrow: "Control Lens",
    title: "لنز کنترل",
    text: "برای پیام‌های همراه با فشار، پیگیری، عجله یا مرزبندی. از نظر مفهومی به سیستم پاداش/کنترل، دوپامین و واکنش استرس نزدیک است.",
    accent: "violet"
  },
  {
    eyebrow: "Safety Lens",
    title: "لنز امنیت",
    text: "برای پیام‌هایی با اضطراب، قهر، سکوت یا ترس از طردشدن. بیشتر با کورتیزول، نیاز به آرام‌سازی و ثبات سروتونینی توضیح داده می‌شود.",
    accent: "cyan"
  },
  {
    eyebrow: "Belonging Lens",
    title: "لنز تعلق",
    text: "برای پیام‌هایی درباره توجه، ارزشمندی، احترام و دیده‌شدن. به‌صورت مفهومی به اکسی‌توسین، پیوند اجتماعی و حس تعلق مربوط است.",
    accent: "green"
  }
];

export default function Home() {
  const [authModalOpen, setAuthModalOpen] = useState(false);
  const [authMode, setAuthMode] = useState<"login" | "signup">("signup");
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [credits, setCredits] = useState(0);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  function openAuthFlow(mode: "login" | "signup") {
    setAuthMode(mode);
    setAuthModalOpen(true);
    setError("");
    setStatus("");
  }

  async function handleOtp() {
    if (!phone.trim()) {
      setError("برای ورود یا ثبت‌نام، شماره موبایل را وارد کنید.");
      return;
    }
    setError("");
    setStatus("در حال ارسال کد فعال‌سازی...");
    try {
      const result = await requestOtp(phone);
      setOtpSent(true);
      setStatus(result.dev_otp_code ? `کد تست صادر شد: ${result.dev_otp_code}` : "کد تایید ارسال شد.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "ارسال کد تایید ناموفق بود.");
      setStatus("");
    }
  }

  async function handleVerify() {
    if (!otp.trim()) {
      setError("کد تایید را وارد کنید.");
      return;
    }
    setError("");
    setStatus("در حال تایید کد...");
    try {
      const result = await verifyOtp(phone, otp);
      setCredits(result.credit_balance);
      setStatus("حساب فعال شد و ۱ اعتبار تستی به شما اضافه شد.");
      window.setTimeout(() => setAuthModalOpen(false), 700);
    } catch (err) {
      setError(err instanceof Error ? err.message : "کد وارد شده معتبر نیست.");
      setStatus("");
    }
  }

  return (
    <main className="page">
      <header className="topbar">
        <div className="shell topbar-inner">
          <a className="brand" href="#top" aria-label="Message Decoder">
            <div className="brand-logo">
              <MessageSquareText size={20} />
            </div>
            <div className="brand-text">
              <span className="brand-title">Message Decoder</span>
              <span className="brand-subtitle">by NeuroLens</span>
            </div>
          </a>
          <div className="nav-actions">
            {credits > 0 && (
              <div className="credit-badge">
                <Sparkles size={14} />
                <span>{credits} اعتبار</span>
              </div>
            )}
            <button className="nav-login" onClick={() => openAuthFlow("login")}>
              <LogIn size={14} />
              <span>ورود / ثبت‌نام</span>
            </button>
            <Link className="nav-cta" href="/decoder">
              تحلیل رایگان
            </Link>
          </div>
        </div>
      </header>

      <section className="hero-section" id="top">
        <div className="shell hero-layout">
          <div className="hero-copy">
            <div className="trust-strip">
              <span>برای پیام‌های شریک عاطفی، دوست، خانواده یا مدیر</span>
              <span>تحلیل رفتاری الهام‌گرفته از علوم اعصاب؛ نه ذهن‌خوانی</span>
            </div>
            <h1>قبل از جواب دادن، بفهمید چه برداشتی از پیام محتمل‌تر است.</h1>
            <p className="hero-subtitle">
              Message Decoder پیام‌های مبهم، سرد یا احساسی را با الهام از علوم اعصاب و روان‌شناسی رفتاری بررسی می‌کند. به‌جای حدس‌زدن نیت طرف مقابل، چند نیاز محتمل مثل امنیت، کنترل، تعلق یا دیده‌شدن را می‌بینید و با اضطراب کمتر پاسخ می‌دهید.
            </p>
            <div className="hero-actions">
              <Link className="btn-primary" href="/decoder">
                <Sparkles size={18} />
                <span>تحلیل رایگان پیام اول</span>
              </Link>
              <button className="btn-secondary" onClick={() => openAuthFlow("signup")}>
                <User size={17} />
                <span>ورود یا ساخت حساب</span>
              </button>
              <a className="btn-secondary" href="#how-it-works">
                آشنایی با لنزهای تحلیل
              </a>
            </div>
            <div className="testimonial-chip">
              <span className="quote-mark" aria-hidden="true">
                <Quote size={18} />
              </span>
              <div>
                <p>قبلاً پیام‌های کوتاه را نشانه بی‌علاقگی می‌دیدم. حالا قبل از پاسخ، احتمال‌های انسانی‌تری مثل نیاز به اطمینان را هم بررسی می‌کنم.</p>
                <span className="testimonial-meta">نمونه تجربه کاربر در رابطه عاطفی</span>
              </div>
            </div>
          </div>

          <div className="phone-mockup" aria-label="نمونه تحلیل پیام در موبایل">
            <div className="analysis-popover external-popover">
              <span className="popover-kicker">Safety + Belonging</span>
              <strong>نیاز احتمالی به اطمینان</strong>
              <p>ریسک: پاسخ دفاعی می‌تواند حس دیده‌نشدن را شدیدتر کند.</p>
            </div>
            <div className="safe-reply-card external-card">
              <span>پاسخ کم‌تنش‌تر پیشنهاد شده</span>
              <p>می‌فهمم چرا این حس رو گرفتی. برام مهمی، فقط شاید خوب نشانش ندادم.</p>
            </div>

            <div className="phone-frame">
              <div className="phone-speaker" />
              <div className="dynamic-island" />
              <div className="phone-status">
                <span className="phone-time">09:41</span>
                <div className="phone-status-icons">
                  <span className="phone-signal">📶</span>
                  <span className="phone-battery">🔋</span>
                </div>
              </div>
              <div className="chat-screen ios-chat">
                <div className="ios-navbar">
                  <div className="ios-back-btn">
                    <svg viewBox="0 0 24 24" width="24" height="24"><path d="M15.5 19l-7-7 7-7" stroke="currentColor" strokeWidth="2.5" fill="none" strokeLinecap="round" strokeLinejoin="round"/></svg>
                    <span className="ios-badge">3</span>
                  </div>
                  <div className="ios-contact">
                    <div className="ios-avatar">آ</div>
                    <span className="ios-name">علی</span>
                  </div>
                </div>

                <div className="chat-content">
                  <div className="chat-bubble incoming long-message ios-bubble">
                    باشه، هر جور راحتی. فقط جالبه که وقتی من چیزی می‌خوام همیشه باید توضیح بدم چرا ناراحتم. انگار اصلاً مهم نیست که چند بار همین موضوع رو گفته‌ام.
                    <div className="ios-tail"></div>
                  </div>
                  <div className="scanner-band" />
                  
                  <div className="draft-loop" aria-label="چند تلاش برای نوشتن پاسخ که پاک می‌شوند">
                    <div className="draft-row draft-one">
                      <span>خب اگه اینطوری فکر می‌کنی...</span>
                      <i />
                    </div>
                    <div className="draft-row draft-two">
                      <span>من که کاری نکردم، چرا همیشه...</span>
                      <i />
                    </div>
                    <div className="draft-row draft-three">
                      <span>باشه، ولی می‌خوام درست جواب بدم.</span>
                      <i />
                    </div>
                  </div>
                </div>

                <div className="ios-input-capsule">
                  <span className="ios-add-btn">+</span>
                  <div className="ios-input-field">
                    <span className="ios-placeholder">iMessage</span>
                    <span className="ios-mic">
                      <svg width="14" height="20" viewBox="0 0 14 20" fill="currentColor"><path d="M7 13c1.66 0 3-1.34 3-3V3c0-1.66-1.34-3-3-3S4 1.34 4 3v7c0 1.66 1.34 3 3 3z"/><path d="M13 10c0 3.31-2.69 6-6 6s-6-2.69-6-6H0c0 3.53 2.61 6.43 6 6.92V20h2v-3.08c3.39-.49 6-3.39 6-6.92h-1z"/></svg>
                    </span>
                  </div>
                </div>

                <div className="ios-keyboard animated-keyboard">
                  <div className="keyboard-predictions">
                    <span>خب</span>
                    <span>من</span>
                    <span>باشه</span>
                  </div>
                  <div className="keyboard-row">
                    <kbd>ض</kbd><kbd>ص</kbd><kbd>ث</kbd><kbd>ق</kbd><kbd>ف</kbd><kbd>غ</kbd><kbd>ع</kbd><kbd>ه</kbd><kbd className="anim-k-1">خ</kbd><kbd>ح</kbd><kbd>ج</kbd><kbd>چ</kbd>
                  </div>
                  <div className="keyboard-row">
                    <kbd>ش</kbd><kbd>س</kbd><kbd>ی</kbd><kbd className="anim-k-2">ب</kbd><kbd>ل</kbd><kbd>ا</kbd><kbd>ت</kbd><kbd>ن</kbd><kbd>م</kbd><kbd>ک</kbd><kbd>گ</kbd>
                  </div>
                  <div className="keyboard-row">
                    <kbd className="key-shift">⇧</kbd>
                    <kbd>ظ</kbd><kbd>ط</kbd><kbd>ز</kbd><kbd>ر</kbd><kbd>ذ</kbd><kbd>د</kbd><kbd>پ</kbd><kbd>و</kbd>
                    <kbd className="key-delete anim-k-del">⌫</kbd>
                  </div>
                  <div className="keyboard-row">
                    <kbd className="key-num">123</kbd>
                    <kbd className="key-space anim-k-space">فاصله</kbd>
                    <kbd className="key-return">return</kbd>
                  </div>
                </div>
              </div>
              <div className="home-indicator" />
            </div>
          </div>
        </div>
      </section>

      <section className="neuroscience-section">
        <div className="shell science-layout">
          <div>
            <span className="section-kicker">Neuro-Structured Analysis</span>
            <h2>تحلیل رفتاری، با احتیاط علمی</h2>
          </div>
          <div className="story-copy">
            <p>وقتی آدم‌ها احساس فشار، طردشدن، بی‌توجهی یا از دست دادن کنترل می‌کنند، واکنش‌هایشان معمولاً الگوهای قابل‌فهم‌تری پیدا می‌کند. Message Decoder از همین الگوها کمک می‌گیرد تا پیام را فقط از سطح کلمات نخواند.</p>
            <p>این ابزار ادعا نمی‌کند ذهن طرف مقابل را می‌خواند. خروجی آن یک برداشت قطعی نیست؛ چند چرایی محتمل است که کمک می‌کند قبل از پاسخ، موقعیت را انسانی‌تر و دقیق‌تر ببینید.</p>
          </div>
        </div>
      </section>

      <section className="benefits-section">
        <div className="shell">
          <div className="benefit-grid">
            {benefitCards.map((benefit) => {
              const Icon = benefit.icon;
              return (
                <article className="benefit-card" key={benefit.title}>
                  <div className="benefit-icon">
                    <Icon size={22} />
                  </div>
                  <h3>{benefit.title}</h3>
                  <p>{benefit.text}</p>
                </article>
              );
            })}
          </div>
        </div>
      </section>

      <section className="lenses-section" id="how-it-works">
        <div className="shell">
          <div className="section-heading">
            <span>لنزهای تحلیل</span>
            <h2>هر پیام را از سه لنز انسانی ببینید</h2>
            <p>لحن، زمینه، نوع رابطه و شدت واکنش کنار هم قرار می‌گیرند تا نیاز احتمالی پشت پیام واضح‌تر شود. اشاره به هورمون‌ها در این بخش توضیح مفهومی است، نه تشخیص پزشکی.</p>
          </div>
          <div className="lens-grid">
            {lensCards.map((lens) => (
              <article className={`lens-card ${lens.accent}`} key={lens.title}>
                <span>{lens.eyebrow}</span>
                <h3>{lens.title}</h3>
                <p>{lens.text}</p>
              </article>
            ))}
          </div>
        </div>
      </section>

      <section className="story-section">
        <div className="shell story-layout">
          <div>
            <span className="section-kicker">لحظه تصمیم</span>
            <h2>گاهی یک پیام کوتاه، چند ساعت فکر و نگرانی می‌سازد.</h2>
          </div>
          <div className="story-copy">
            <p>«معلومه که اصلاً برات مهم نیست.» یا از طرف مدیرتان: «چرا باید دوباره پیگیری کنم؟» شاید چند جواب بنویسید، پاک کنید و دوباره از اول شروع کنید.</p>
            <p>Message Decoder پیام را در زمینه رابطه می‌بیند، نیاز احتمالی پشت واکنش را نشان می‌دهد و کمک می‌کند به جای پاسخ دفاعی، پاسخی روشن، آرام و قابل دفاع بسازید.</p>
          </div>
        </div>
      </section>

      <section className="before-after-section">
        <div className="shell">
          <div className="section-heading">
            <span>قبل و بعد</span>
            <h2>قبل از واکنش نشان دادن، یک‌بار واضح‌تر ببینید</h2>
          </div>
          <div className="comparison-grid">
            <article className="comparison-card bad">
              <span>قبل: پاسخ دفاعی</span>
              <p>خب اگه اینطوری فکر می‌کنی هر جور راحتی. من که کاری نکردم.</p>
              <strong>ریسک: سرد، مبهم و تشدیدکننده تنش</strong>
            </article>
            <article className="comparison-card good">
              <span>بعد: پاسخ کم‌تنش‌تر</span>
              <p>می‌فهمم چرا اینطور برداشت کردی. قصدم بی‌اهمیت کردن تو نبود. اگر مستقیم‌تر بگی چی اذیتت کرده، بهتر می‌تونم جواب بدم.</p>
              <strong>نتیجه: احساس دیده‌شدن + مرزبندی آرام</strong>
            </article>
          </div>
        </div>
      </section>

      <section className="final-cta-section">
        <div className="shell final-cta">
          <h2>برای پاسخ دادن هنوز مطمئن نیستید؟</h2>
          <p>یک پیام مبهم را در صفحه ابزار وارد کنید. Message Decoder چند برداشت محتمل، ریسک سوءتفاهم و مسیر پاسخ کم‌تنش‌تر را نشان می‌دهد.</p>
          <Link className="btn-primary" href="/decoder">
            <Sparkles size={18} />
            <span>رفتن به ابزار تحلیل پیام</span>
          </Link>
        </div>
      </section>

      {authModalOpen && (
        <div className="modal-backdrop" role="dialog" aria-modal="true" aria-label="ورود یا ثبت‌نام">
          <div className="auth-modal">
            <button className="modal-close" onClick={() => setAuthModalOpen(false)} aria-label="بستن">
              ×
            </button>
            <div className="auth-modal-header">
              <span>{authMode === "signup" ? "ثبت‌نام سریع" : "ورود سریع"}</span>
              <h2>{authMode === "signup" ? "با شماره موبایل شروع کنید" : "به حساب خود برگردید"}</h2>
              <p>با هر ورود موفق، ۱ اعتبار تستی به حساب شما اضافه می‌شود. تحلیل رایگان در صفحه ابزار انجام می‌شود.</p>
            </div>

            {status && (
              <div className="toast-msg toast-success">
                <Check size={16} />
                <span>{status}</span>
              </div>
            )}
            {error && (
              <div className="toast-msg toast-error">
                <AlertCircle size={16} />
                <span>{error}</span>
              </div>
            )}

            <div className="auth-grid">
              <div className="auth-row">
                <input
                  type="tel"
                  placeholder="09123456789"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                />
                <button className="btn-secondary" onClick={handleOtp}>
                  <LogIn size={15} /> ارسال کد
                </button>
              </div>

              {otpSent && (
                <div className="auth-row">
                  <input
                    type="text"
                    placeholder="کد تایید"
                    value={otp}
                    onChange={(event) => setOtp(event.target.value)}
                  />
                  <button className="btn-primary btn-compact" onClick={handleVerify}>
                    تایید و دریافت اعتبار
                  </button>
                </div>
              )}
              <span className="field-hint">کد تست: 25367286503</span>
            </div>

            <Link className="auth-free-link" href="/decoder" onClick={() => setAuthModalOpen(false)}>
              رفتن به ابزار تحلیل رایگان
            </Link>
          </div>
        </div>
      )}

      <footer className="footer">
        <div className="shell">
          <p className="footer-text">
            Message Decoder ابزار هوش مصنوعی برای تحلیل زبانی و کمک به پاسخ‌دادن است. این ابزار ذهن‌خوانی نمی‌کند و جایگزین گفت‌وگوی واقعی، مشاوره تخصصی، درمان یا اقدام اضطراری نیست.
          </p>
        </div>
      </footer>
    </main>
  );
}
