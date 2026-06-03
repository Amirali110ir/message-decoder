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
  Sparkles
} from "lucide-react";
import Link from "next/link";
import { useEffect, useRef, useState } from "react";
import { notifyTelegramOtp, requestOtp, verifyOtp } from "../lib/api";
import { faNum } from "../lib/format";

const benefitCards = [
  {
    icon: ShieldAlert,
    title: "قبل از دفاع کردن، ریسک را ببینید",
    text: "یک پیام سرد می‌تواند از دلخوری، عجله یا نیاز به اطمینان آمده باشد. قبل از جواب تند، برداشت‌های محتمل را کنار هم ببینید."
  },
  {
    icon: Compass,
    title: "از یک جمله، فقط یک داستان نسازید",
    text: "وقتی شریک عاطفی، دوست یا مدیرتان مبهم حرف می‌زند، ابزار نشان می‌دهد کدام نیاز یا نگرانی ممکن است پشت پیام باشد."
  },
  {
    icon: ClipboardCheck,
    title: "جواب قابل ارسال، نه توصیه کلی",
    text: "بعد از تحلیل، پاسخ‌های نرم، قاطع، کوتاه یا پایان‌دهنده می‌سازید؛ قابل کپی، قابل ویرایش و مناسب همان موقعیت."
  }
];

const lensCards = [
  {
    eyebrow: "Control Lens",
    title: "لنز نتیجه و کنترل",
    text: "برای پیام‌هایی که بوی فشار، پیگیری، عجله یا مرزبندی می‌دهند. کمک می‌کند بفهمید طرف مقابل بیشتر دنبال خروجی، زمان‌بندی یا کنترل موقعیت است.",
    accent: "violet"
  },
  {
    eyebrow: "Safety Lens",
    title: "لنز امنیت و اعتماد",
    text: "برای پیام‌هایی که پشت آن اضطراب، قهر، سکوت یا ترس از بی‌اهمیت شدن دیده می‌شود. کمک می‌کند قبل از پاسخ، نیاز به اطمینان را جدی‌تر ببینید.",
    accent: "cyan"
  },
  {
    eyebrow: "Respect Lens",
    title: "لنز شأن و تعلق",
    text: "برای پیام‌هایی درباره احترام، ارزشمندی، دیده‌شدن یا جایگاه. کمک می‌کند پاسخ شما هم رابطه را ببیند، هم مرزتان را حفظ کند.",
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
  const [heroMessage, setHeroMessage] = useState("");
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const modalRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    if (!authModalOpen) return;
    const previouslyFocused = document.activeElement as HTMLElement | null;
    const focusables = () =>
      Array.from(
        modalRef.current?.querySelectorAll<HTMLElement>(
          'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled])'
        ) ?? []
      );
    focusables()[0]?.focus();

    function onKey(event: KeyboardEvent) {
      if (event.key === "Escape") {
        setAuthModalOpen(false);
        return;
      }
      if (event.key !== "Tab") return;
      const items = focusables();
      if (items.length === 0) return;
      const first = items[0];
      const last = items[items.length - 1];
      const active = document.activeElement;
      if (event.shiftKey && active === first) {
        event.preventDefault();
        last.focus();
      } else if (!event.shiftKey && active === last) {
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

  function openAuthFlow(mode: "login" | "signup") {
    setAuthMode(mode);
    setAuthModalOpen(true);
    setError("");
    setStatus("");
  }

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
                <span>{faNum(credits)} اعتبار</span>
              </div>
            )}
            <button className="nav-login" onClick={() => openAuthFlow("login")}>
              <LogIn size={14} />
              <span>ورود / اعتبار</span>
            </button>
            <Link className="nav-cta" href="/decoder">
              تحلیل پیام
            </Link>
          </div>
        </div>
      </header>

      <section className="hero-section" id="top">
        <div className="shell hero-layout">
          <div className="hero-copy">
            <div className="trust-strip">
              <span>تحلیل اول رایگان و بدون ثبت‌نام</span>
              <span>خصوصی؛ متن حساس ذخیره نمی‌شود</span>
            </div>
            <h1>پیام مبهم را بفهمید؛ با اضطراب کمتر جواب بدهید.</h1>
            <p className="hero-subtitle">
              متن پیام را بگذارید تا برداشت محتمل، ریسک سوءتفاهم و مسیر پاسخ کم‌تنش‌تر را ببینید. Message Decoder ذهن‌خوانی نمی‌کند؛ فقط کمک می‌کند قبل از واکنش، چند احتمال انسانی‌تر را بررسی کنید.
            </p>
            <div className="hero-mini-form">
              <textarea
                value={heroMessage}
                onChange={(event) => setHeroMessage(event.target.value)}
                placeholder="پیام مبهمی که دریافت کردید را اینجا بگذارید..."
                rows={3}
              />
              <button
                className="btn-primary"
                onClick={() => {
                  const path = heroMessage.trim()
                    ? `/decoder?msg=${encodeURIComponent(heroMessage.trim())}`
                    : "/decoder";
                  window.location.assign(path);
                }}
              >
                <Sparkles size={18} />
                <span>تحلیل رایگان این پیام</span>
              </button>
            </div>
            <div className="testimonial-chip">
              <span className="quote-mark" aria-hidden="true">
                <Quote size={18} />
              </span>
              <div>
                <p>قبلاً پیام‌های کوتاه را سریع نشانه بی‌علاقگی می‌دیدم. حالا قبل از جواب دادن، یک بار هم از زاویه اطمینان، احترام و سوءتفاهم نگاه می‌کنم.</p>
                <span className="testimonial-meta">نمونه تجربه کاربر بعد از تحلیل پیام</span>
              </div>
            </div>
          </div>

          <div className="phone-mockup" aria-label="نمونه تحلیل پیام در موبایل">
            <div className="analysis-popover external-popover">
              <span className="popover-kicker">امنیت و اطمینان</span>
              <strong>احتمال نیاز به اطمینان</strong>
              <p>ریسک: جواب دفاعی می‌تواند حس دیده‌نشدن را بیشتر کند.</p>
            </div>
            <div className="safe-reply-card external-card">
              <span>پاسخ قابل ارسال</span>
              <p>می‌فهمم چرا این برداشت رو کردی. برام مهمی؛ فقط احتمالاً خوب نشانش ندادم.</p>
            </div>

            <div className="phone-frame">
              <div className="phone-speaker" />
              <div className="dynamic-island" />
              <div className="phone-status">
                <span className="phone-time">09:41</span>
                <div className="phone-status-icons">
                  <span className="phone-signal" aria-hidden="true">
                    <svg width="17" height="11" viewBox="0 0 17 11" fill="currentColor">
                      <rect x="0" y="8" width="3" height="3" rx="0.5" />
                      <rect x="4.5" y="5.5" width="3" height="5.5" rx="0.5" />
                      <rect x="9" y="3" width="3" height="8" rx="0.5" />
                      <rect x="13.5" y="0" width="3" height="11" rx="0.5" />
                    </svg>
                  </span>
                  <span className="phone-battery" aria-hidden="true">
                    <svg width="25" height="12" viewBox="0 0 25 12" fill="none">
                      <rect x="0.5" y="0.5" width="21" height="11" rx="3" stroke="currentColor" opacity="0.4" />
                      <rect x="2" y="2" width="18" height="8" rx="1.5" fill="currentColor" />
                      <rect x="23" y="4" width="1.5" height="4" rx="0.75" fill="currentColor" opacity="0.4" />
                    </svg>
                  </span>
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
                    باشه، هر جور راحتی. فقط جالبه که هر وقت من چیزی می‌خوام، باید توضیح بدم چرا ناراحتم. انگار اصلاً مهم نیست چند بار گفته‌ام.
                    <div className="ios-tail"></div>
                  </div>
                  <div className="scanner-band" />
                  
                  <div className="draft-loop" aria-label="چند تلاش برای نوشتن پاسخ که پاک می‌شوند">
                    <div className="draft-row draft-one">
                      <span>خب اگه اینطوری فکر می‌کنی...</span>
                      <i />
                    </div>
                    <div className="draft-row draft-two">
                      <span>من که کاری نکردم، چرا اینقدر...</span>
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
            <h2>ببینید پیام بیشتر از کدام نیاز می‌آید</h2>
            <p>لحن، زمینه، نوع رابطه و هدف پاسخ کنار هم قرار می‌گیرند تا بفهمید احتمالاً باید آرام‌سازی کنید، مرز بگذارید، مسئولیت روشن کنید یا فقط سوءتفاهم را کم کنید.</p>
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

      <section className="before-after-section">
        <div className="shell">
          <div className="section-heading">
            <span>قبل و بعد</span>
            <h2>یک مکث کوتاه، جواب را از دفاعی به روشن تبدیل می‌کند</h2>
          </div>
          <div className="comparison-grid">
            <article className="comparison-card bad">
              <span>قبل: پاسخ دفاعی</span>
              <p>خب اگه اینطوری فکر می‌کنی هر جور راحتی. من که کاری نکردم.</p>
              <strong>ریسک: سرد، مبهم و تشدیدکننده تنش</strong>
            </article>
            <article className="comparison-card good">
              <span>بعد: پاسخ کم‌تنش‌تر</span>
              <p>می‌فهمم چرا این برداشت رو کردی. قصدم بی‌اهمیت کردن تو نبود. اگر مستقیم‌تر بگی چی اذیتت کرده، بهتر می‌تونم جواب بدم.</p>
              <strong>نتیجه: احساس دیده‌شدن + مرزبندی آرام</strong>
            </article>
          </div>
        </div>
      </section>

      <section className="final-cta-section">
        <div className="shell final-cta">
          <h2>قبل از اینکه جواب را بفرستید، یک بار پیام را تحلیل کنید.</h2>
          <p>تحلیل اولیه بدون ورود است. پیام را وارد کنید، برداشت محتمل و ریسک پاسخ عجولانه را ببینید، بعد اگر خواستید پاسخ کامل بسازید.</p>
          <Link className="btn-primary" href="/decoder">
            <Sparkles size={18} />
            <span>تحلیل پیامم را شروع کنم</span>
          </Link>
          <a className="btn-secondary" href="https://t.me/MeDecoderBot" target="_blank" rel="noreferrer">
            رفتن به بات تلگرام
          </a>
        </div>
      </section>

      {authModalOpen && (
        <div
          className="modal-backdrop"
          role="dialog"
          aria-modal="true"
          aria-label="ورود و دریافت اعتبار"
          onClick={() => setAuthModalOpen(false)}
        >
          <div className="auth-modal" ref={modalRef} onClick={(event) => event.stopPropagation()}>
            <button className="modal-close" onClick={() => setAuthModalOpen(false)} aria-label="بستن">
              ×
            </button>
            <div className="auth-modal-header">
              <span>{authMode === "signup" ? "ورود و اعتبار" : "ورود سریع"}</span>
              <h2>{authMode === "signup" ? "پاسخ کامل را با اعتبار حساب بسازید" : "با شماره موبایل به حسابتان برگردید"}</h2>
              <p>برای تحلیل اولیه در وب لازم نیست وارد شوید. برای پاسخ‌های قابل کپی، کد ورود را با SMS/OTP می‌گیرید؛ اگر حساب تلگرام همین شماره را داشته باشد، کد ورود داخل تلگرام هم ارسال می‌شود.</p>
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
                  inputMode="tel"
                  autoComplete="tel"
                  placeholder="09123456789"
                  value={phone}
                  onChange={(event) => setPhone(event.target.value)}
                />
                <button className="btn-secondary" onClick={handleOtp}>
                  <LogIn size={15} /> گرفتن کد ورود
                </button>
              </div>

              {otpSent && (
                <div className="auth-row">
                  <input
                    type="text"
                    inputMode="numeric"
                    autoComplete="one-time-code"
                    placeholder="کد ورود"
                    value={otp}
                    onChange={(event) => setOtp(event.target.value)}
                  />
                  <button className="btn-primary btn-compact" onClick={handleVerify}>
                    ورود و فعال‌سازی اعتبار
                  </button>
                </div>
              )}
            </div>

            <Link className="auth-free-link" href="/decoder" onClick={() => setAuthModalOpen(false)}>
              اول تحلیل رایگان را ببینم
            </Link>
          </div>
        </div>
      )}

      <footer className="footer">
        <div className="shell">
          <p className="footer-text">
            Message Decoder برای تحلیل زبانی و ساخت پاسخ کم‌تنش‌تر است. این ابزار ذهن‌خوانی نمی‌کند، تشخیص روان‌شناختی نمی‌دهد و جایگزین گفت‌وگوی واقعی، مشاوره تخصصی، درمان یا اقدام اضطراری نیست.
          </p>
        </div>
      </footer>
    </main>
  );
}
