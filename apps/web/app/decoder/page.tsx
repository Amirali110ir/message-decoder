"use client";

import {
  Activity,
  AlertCircle,
  Award,
  BrainCircuit,
  Check,
  Compass,
  Copy,
  CreditCard,
  EyeOff,
  Fingerprint,
  Flame,
  Glasses,
  HeartHandshake,
  LockKeyhole,
  LogIn,
  MessageCircle,
  MessageSquareCode,
  MessageSquareText,
  Radar,
  RefreshCw,
  Scale,
  ShieldAlert,
  Sparkles,
  Target,
  User,
  Users,
  Zap
} from "lucide-react";
import Link from "next/link";
import { useState } from "react";
import {
  copyEvent,
  createPayment,
  freeDecode,
  FreeDecodeResponse,
  paidDecode,
  PaidDecodeResponse,
  requestOtp,
  sendFeedback,
  verifyPayment,
  verifyOtp
} from "../../lib/api";

const relationshipOptions = [
  ["romantic", "رابطه عاطفی"],
  ["ex", "اکس / رابطه تمام‌شده"],
  ["friend", "دوست یا آشنا"],
  ["family", "خانواده"],
  ["manager_colleague", "مدیر یا همکار"],
  ["customer", "مشتری یا خریدار"],
  ["unknown", "نامشخص"]
] as const;

const goalOptions = [
  ["calm_conflict", "دعوا آرام شود"],
  ["set_boundary", "مرز محکم بگذارم"],
  ["improve_relationship", "رابطه بهتر شود"],
  ["professional_reply", "جواب حرفه‌ای بدهم"],
  ["make_them_accountable", "طرف مقابل مسئولیت بپذیرد"],
  ["avoid_needy", "ضعیف یا آویزان دیده نشوم"],
  ["end_conversation", "مکالمه را ببندم"],
  ["understand_only", "فقط بفهمم منظورش چیست"]
] as const;

export default function DecoderPage() {
  const [message, setMessage] = useState("");
  const [relationship, setRelationship] = useState("romantic");
  const [goal, setGoal] = useState("avoid_needy");
  const [context, setContext] = useState("");
  const [consent, setConsent] = useState<"none" | "history" | "anonymized">("none");
  const [freeResult, setFreeResult] = useState<FreeDecodeResponse | null>(null);
  const [paidResult, setPaidResult] = useState<PaidDecodeResponse | null>(null);
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [token, setToken] = useState("");
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);

  async function handleFreeDecode() {
    if (!message.trim()) return;
    setError("");
    setLoading(true);
    setStatus("در حال بررسی پیام و انتخاب لنزهای محتمل...");
    setPaidResult(null);
    try {
      const result = await freeDecode({
        message_text: message,
        relationship_type: relationship as never,
        user_goal: goal as never,
        optional_context: context || undefined,
        privacy_consent: consent
      });
      setFreeResult(result);
      setStatus("تحلیل رایگان آماده شد. حالا می‌توانید برداشت‌های محتمل را ببینید.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "ارتباط با سرور تحلیل برقرار نشد. لطفاً دوباره تلاش کنید.");
      setStatus("");
    } finally {
      setLoading(false);
    }
  }

  async function handleOtp() {
    if (!phone.trim()) {
      setError("برای فعال‌سازی پاسخ کامل، شماره موبایل را وارد کنید.");
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
      setToken(result.token);
      setCredits(result.credit_balance);
      setStatus("حساب فعال شد و ۱ اعتبار تستی اضافه شد. حالا می‌توانید پاسخ کامل بسازید.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "کد وارد شده معتبر نیست.");
      setStatus("");
    }
  }

  async function handleBuyCredits() {
    if (!token) {
      setError("ابتدا شماره موبایل را تایید کنید.");
      return;
    }
    setError("");
    setStatus("در حال فعال‌سازی اعتبار تستی...");
    try {
      const payment = await createPayment(token, "credits_5");
      const verified = await verifyPayment(token, payment.payment_id);
      setCredits(verified.credit_balance);
      setStatus("۵ اعتبار تستی به حساب شما اضافه شد.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "فعال‌سازی اعتبار تستی ناموفق بود.");
      setStatus("");
    }
  }

  async function handlePaidDecode() {
    if (!freeResult) return;
    if (!token) {
      setError("برای ساخت پاسخ‌های آماده، ابتدا شماره موبایل را تایید کنید.");
      return;
    }
    setError("");
    setLoading(true);
    setStatus("در حال ساخت پاسخ‌های نرم، قاطع و کم‌تنش...");
    try {
      const result = await paidDecode(token, freeResult.decode_id);
      setPaidResult(result);
      setCredits(result.credit_balance);
      setStatus("پاسخ‌های پیشنهادی آماده شدند. یکی را انتخاب کنید و با اطمینان بیشتری ارسال کنید.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "ساخت پاسخ کامل ناموفق بود.");
      setStatus("");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy(text: string, label: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(label);
      if (freeResult) {
        await copyEvent(freeResult.decode_id, label, label);
      }
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      setError("کپی خودکار انجام نشد. متن را دستی کپی کنید.");
    }
  }

  async function handleFeedback(user_rating: string, outcome?: string, regret_score?: number) {
    if (!freeResult) return;
    try {
      await sendFeedback({
        decode_id: freeResult.decode_id,
        user_rating,
        outcome,
        regret_score,
        copied_response: Boolean(paidResult)
      });
      setStatus("بازخورد شما ثبت شد. ممنون که محصول را دقیق‌تر می‌کنید.");
    } catch (err) {
      // Feedback should never interrupt the main flow.
    }
  }

  return (
    <main className="page decoder-page">
      <header className="topbar">
        <div className="shell topbar-inner">
          <Link className="brand" href="/" aria-label="Message Decoder">
            <div className="brand-logo">
              <MessageSquareText size={20} />
            </div>
            <div className="brand-text">
              <span className="brand-title">Message Decoder</span>
              <span className="brand-subtitle">ابزار تحلیل پیام</span>
            </div>
          </Link>
          <div className="nav-actions">
            {token ? (
              <>
                <div className="account-badge">
                  <User size={14} />
                  <span>{phone}</span>
                </div>
                <div className="credit-badge">
                  <Zap size={14} />
                  <span>{credits} اعتبار</span>
                </div>
              </>
            ) : (
              <div className="credit-badge">
                <Zap size={14} />
                <span>رایگان</span>
              </div>
            )}
            <Link className="nav-login" href="/">
              بازگشت
            </Link>
          </div>
        </div>
      </header>

      <section className="decoder-section decoder-app-section" id="decoder">
        <div className="shell">
          <div className="section-heading">
            <span>ابزار Message Decoder</span>
            <h1>پیام را وارد کنید؛ قبل از پاسخ، واضح‌تر ببینید</h1>
            <p>تحلیل اولیه بدون ورود انجام می‌شود. برای ساخت پاسخ‌های کامل، همان‌جا با شماره موبایل وارد می‌شوید و اعتبار تستی می‌گیرید.</p>
          </div>

          <div className="workspace-grid">
            <div className="panel-card form-grid">
              <div className="panel-title">
                <MessageSquareCode size={19} />
                <div>
                  <h3>متن پیام</h3>
                  <p>پیام را همان‌طور که دریافت کرده‌اید وارد کنید؛ نام، شماره و اطلاعات حساس را حذف کنید.</p>
                </div>
              </div>

              <div className="field-group">
                <label className="field-label">
                  <MessageCircle size={16} />
                  <span>متن پیام</span>
                </label>
                <textarea
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="مثلاً: باشه، هر جور راحتی. معلومه که اصلاً برات مهم نیست."
                />
              </div>

              <div className="form-row">
                <div className="field-group">
                  <label className="field-label">
                    <Users size={16} />
                    <span>نوع رابطه</span>
                  </label>
                  <select value={relationship} onChange={(event) => setRelationship(event.target.value)}>
                    {relationshipOptions.map(([value, label]) => (
                      <option value={value} key={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>

                <div className="field-group">
                  <label className="field-label">
                    <Target size={16} />
                    <span>هدف پاسخ</span>
                  </label>
                  <select value={goal} onChange={(event) => setGoal(event.target.value)}>
                    {goalOptions.map(([value, label]) => (
                      <option value={value} key={value}>
                        {label}
                      </option>
                    ))}
                  </select>
                </div>
              </div>

              <div className="field-group">
                <label className="field-label">
                  <Fingerprint size={16} />
                  <span>زمینه کوتاه، اگر لازم است</span>
                </label>
                <input
                  value={context}
                  onChange={(event) => setContext(event.target.value)}
                  placeholder="مثلاً: بعد از اینکه دیر جواب دادم این پیام را فرستاد..."
                />
              </div>

              <div className="field-group">
                <label className="field-label">
                  <EyeOff size={16} />
                  <span>حریم خصوصی</span>
                </label>
                <select value={consent} onChange={(event) => setConsent(event.target.value as never)}>
                  <option value="none">پیام من ذخیره نشود.</option>
                  <option value="history">فقط در تاریخچه حساب من ذخیره شود.</option>
                  <option value="anonymized">به‌صورت ناشناس برای بهبود مدل استفاده شود.</option>
                </select>
              </div>

              <button className="btn-primary btn-wide" onClick={handleFreeDecode} disabled={!message.trim() || loading}>
                {loading ? <RefreshCw className="animate-spin" size={18} /> : <Sparkles size={18} />}
                <span>تحلیل رایگان پیام</span>
              </button>
            </div>

            <div className="panel-card results-panel">
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

              {freeResult ? (
                <div className="results-container">
                  <div className="panel-title">
                    <Radar size={19} />
                    <div>
                      <h3>این پیام از کدام نیازها می‌تواند آمده باشد؟</h3>
                      <p>لنز غالب، ریسک سوءتفاهم و مسیر پاسخ پیشنهادی آماده است.</p>
                    </div>
                  </div>

                  {freeResult.safety_output && (
                    <div className="result-card safety-alert-card">
                      <div className="lens-header">
                        <span className="lens-badge danger">
                          <ShieldAlert size={14} /> {freeResult.safety_output.warning_title}
                        </span>
                        <span className="confidence-badge">شدت: {freeResult.safety_output.priority}</span>
                      </div>
                      <h3>توصیه فوری ایمنی ارتباط</h3>
                      <p>{freeResult.safety_output.recommendation}</p>
                      <div className="reply-bubble">{freeResult.safety_output.suggested_reply}</div>
                    </div>
                  )}

                  {freeResult.free_output && (
                    <>
                      <div className="result-card hero-result-card">
                        <div className="lens-header">
                          <span className="lens-badge">
                            <Glasses size={14} />
                            <span>{freeResult.free_output.dominant_lens.fa}</span>
                          </span>
                        <span className="confidence-badge">اطمینان تحلیل: {freeResult.free_output.confidence}</span>
                        </div>
                        <h3>برداشت محتمل اصلی</h3>
                        <p>{freeResult.free_output.dominant_lens_explanation}</p>
                      </div>

                      <div className="result-card">
                        <h3>
                          <Activity size={14} /> چرا این لنز انتخاب شد؟
                        </h3>
                        <p>{freeResult.free_output.why_this_lens}</p>
                      </div>

                      <div className="result-card">
                        <h3>
                          <HeartHandshake size={14} /> نیاز یا نگرانی احتمالی
                        </h3>
                        <p>{freeResult.free_output.likely_underlying_need}</p>
                      </div>

                      <div className="result-card warning-card">
                        <h3>
                          <Flame size={14} /> ریسک پاسخ عجولانه چیست؟
                        </h3>
                        <p>{freeResult.free_output.conversation_risk}</p>
                      </div>

                      <div className="result-card success-card">
                        <h3>
                          <Compass size={14} /> مسیر پاسخ کم‌تنش‌تر
                        </h3>
                        <p>{freeResult.free_output.recommended_direction}</p>
                      </div>

                      <div className="result-card">
                        <h3>
                          <Scale size={14} /> برداشت جایگزین
                        </h3>
                        <p>{freeResult.free_output.alternative_read}</p>
                      </div>

                      {freeResult.free_output.privacy_warning && (
                        <div className="result-card danger-card">
                          <h3>
                            <ShieldAlert size={14} /> هشدار حریم خصوصی
                          </h3>
                          <p>{freeResult.free_output.privacy_warning}</p>
                        </div>
                      )}

                      <div className="feedback-box">
                        <span>این تحلیل چقدر به حس شما از موقعیت نزدیک بود؟</span>
                        <div className="feedback-buttons">
                          {["دقیق و عمیق", "نسبتاً نزدیک", "کمی سطحی", "اشتباه"].map((rating) => (
                            <button className="feedback-btn" key={rating} onClick={() => handleFeedback(rating)}>
                              {rating}
                            </button>
                          ))}
                        </div>
                      </div>

                      {!paidResult && (
                        <div className="premium-lock-card">
                          <div className="premium-lock-header">
                            <div className="premium-lock-icon">
                              <Award size={24} />
                            </div>
                            <div className="premium-lock-details">
                              <span>قدم بعدی</span>
                              <h3>۳ پاسخ پیشنهادی بسازید: نرم، قاطع و کوتاه</h3>
                              <p>برای همین موقعیت، جواب‌هایی بسازید که هم روشن باشند، هم تنش را بی‌دلیل بیشتر نکنند.</p>
                            </div>
                          </div>

                          {!token ? (
                            <div className="auth-grid">
                              <div className="auth-title">
                                <LockKeyhole size={16} />
                                <span>فعال‌سازی سریع با شماره همراه</span>
                              </div>
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
                                    تایید و ادامه
                                  </button>
                                </div>
                              )}
                              <span className="field-hint">کد تست: 25367286503</span>
                            </div>
                          ) : (
                            <div className="auth-actions-group">
                              <button className="btn-secondary" onClick={handleBuyCredits}>
                                <CreditCard size={16} /> دریافت ۵ اعتبار تستی
                              </button>
                              <button className="btn-primary" onClick={handlePaidDecode} disabled={credits < 1 || loading}>
                                {loading ? <RefreshCw className="animate-spin" size={16} /> : <Sparkles size={16} />}
                                <span>ساخت پاسخ‌های کم‌تنش</span>
                              </button>
                            </div>
                          )}
                        </div>
                      )}
                    </>
                  )}

                  {paidResult && (
                    <div className="deep-results">
                      <div className="deep-results-title">
                        <Award size={20} />
                        <span>پاسخ‌های پیشنهادی برای ارسال</span>
                      </div>

                      <div className="result-card">
                        <h3>خلاصه عمیق‌تر</h3>
                        <p>{paidResult.paid_output.deep_read}</p>
                      </div>

                      {paidResult.paid_output.reply_options.map((reply) => (
                        <div className="reply-option-card" key={reply.label}>
                          <div className="reply-badge">{reply.label}</div>
                          <div className="reply-bubble">{reply.text}</div>
                          <div className="reply-why">
                            <strong>چرا کار می‌کند:</strong> {reply.why_it_works}
                          </div>
                          <button className="btn-secondary copy-btn" onClick={() => handleCopy(reply.text, reply.label)}>
                            {copiedIndex === reply.label ? (
                              <>
                                <Check size={14} />
                                <span>کپی شد</span>
                              </>
                            ) : (
                              <>
                                <Copy size={14} />
                                <span>کپی این پاسخ</span>
                              </>
                            )}
                          </button>
                        </div>
                      ))}

                      <div className="result-card danger-card">
                        <h3>
                          <ShieldAlert size={14} /> کلماتی که بهتر است استفاده نشوند
                        </h3>
                        <div className="words-avoid-container">
                          {paidResult.paid_output.words_to_avoid.map((word, i) => (
                            <span className="word-tag" key={i}>
                              {word}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="feedback-box">
                        <span>اگر این پاسخ را فرستادید، نتیجه چه شد؟</span>
                        <div className="feedback-buttons">
                          <button className="feedback-btn" onClick={() => handleFeedback("paid", "تنش کمتر شد", 1)}>
                            تنش کمتر شد
                          </button>
                          <button className="feedback-btn" onClick={() => handleFeedback("paid", "طرف بهتر توضیح داد", 1)}>
                            طرف بهتر توضیح داد
                          </button>
                          <button className="feedback-btn" onClick={() => handleFeedback("paid", "دعوا بیشتر شد", 4)}>
                            بدتر شد
                          </button>
                          <button className="feedback-btn" onClick={() => handleFeedback("paid", "هنوز نفرستادم")}>
                            هنوز نفرستادم
                          </button>
                        </div>
                      </div>
                    </div>
                  )}
                </div>
              ) : (
                <div className="empty-state">
                  <div className="empty-state-icon">
                    <BrainCircuit size={28} />
                  </div>
                  <h3>برای پاسخ دادن مطمئن نیستید؟</h3>
                  <p>پیام را وارد کنید تا نیاز احتمالی، ریسک سوءتفاهم و مسیر پاسخ کم‌تنش‌تر را ببینید.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}
