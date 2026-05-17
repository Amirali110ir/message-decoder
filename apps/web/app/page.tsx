"use client";

import { Clipboard, CreditCard, ShieldCheck, Sparkles } from "lucide-react";
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
} from "../lib/api";

const relationshipOptions = [
  ["romantic", "رابطه عاطفی"],
  ["ex", "اکس"],
  ["friend", "دوست"],
  ["family", "خانواده"],
  ["manager_colleague", "مدیر / همکار"],
  ["customer", "مشتری"],
  ["unknown", "نامشخص"]
] as const;

const goalOptions = [
  ["calm_conflict", "می‌خواهم دعوا آرام شود."],
  ["set_boundary", "می‌خواهم مرز بگذارم."],
  ["improve_relationship", "می‌خواهم رابطه بهتر شود."],
  ["professional_reply", "می‌خواهم جواب حرفه‌ای بدهم."],
  ["make_them_accountable", "می‌خواهم طرف مقابل مسئولیت بپذیرد."],
  ["avoid_needy", "می‌خواهم ضعیف یا needy دیده نشوم."],
  ["end_conversation", "می‌خواهم مکالمه را تمام کنم."],
  ["understand_only", "فقط می‌خواهم بفهمم منظورش چیست."]
] as const;

export default function Home() {
  const [message, setMessage] = useState("");
  const [relationship, setRelationship] = useState("romantic");
  const [goal, setGoal] = useState("avoid_needy");
  const [context, setContext] = useState("");
  const [consent, setConsent] = useState<"none" | "history" | "anonymized">("none");
  const [freeResult, setFreeResult] = useState<FreeDecodeResponse | null>(null);
  const [paidResult, setPaidResult] = useState<PaidDecodeResponse | null>(null);
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [token, setToken] = useState("");
  const [credits, setCredits] = useState(0);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  async function handleFreeDecode() {
    setError("");
    setStatus("در حال رمزگشایی پیام...");
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
      setStatus("تحلیل رایگان آماده شد.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطا در تحلیل پیام");
      setStatus("");
    }
  }

  async function handleOtp() {
    setError("");
    const result = await requestOtp(phone);
    setStatus(result.dev_otp_code ? `کد تست: ${result.dev_otp_code}` : "کد ارسال شد.");
  }

  async function handleVerify() {
    setError("");
    const result = await verifyOtp(phone, otp);
    setToken(result.token);
    setCredits(result.credit_balance);
    setStatus("ورود انجام شد.");
  }

  async function handleBuyCredits() {
    if (!token) {
      setError("برای خرید کردیت اول با شماره موبایل وارد شو.");
      return;
    }
    const payment = await createPayment(token, "credits_5");
    const verified = await verifyPayment(token, payment.payment_id);
    setCredits(verified.credit_balance);
    setStatus("پرداخت sandbox تایید شد و کردیت اضافه شد.");
  }

  async function handlePaidDecode() {
    if (!freeResult) return;
    if (!token) {
      setError("برای خروجی کامل اول وارد شو.");
      return;
    }
    setError("");
    try {
      const result = await paidDecode(token, freeResult.decode_id);
      setPaidResult(result);
      setCredits(result.credit_balance);
      setStatus("پاسخ‌های کامل آماده شد.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطا در ساخت پاسخ کامل");
    }
  }

  async function handleCopy(text: string, label: string) {
    await navigator.clipboard.writeText(text);
    if (freeResult) {
      await copyEvent(freeResult.decode_id, label, label);
    }
    setStatus("کپی شد.");
  }

  async function handleFeedback(user_rating: string, outcome?: string, regret_score?: number) {
    if (!freeResult) return;
    await sendFeedback({
      decode_id: freeResult.decode_id,
      user_rating,
      outcome,
      regret_score,
      copied_response: Boolean(paidResult)
    });
    setStatus("بازخورد ثبت شد.");
  }

  return (
    <main className="page">
      <div className="shell">
        <header className="topbar">
          <div className="brand">
            Message Decoder
            <span>by NeuroLens</span>
          </div>
          <div className="hint">کردیت: {credits}</div>
        </header>

        <section className="hero">
          <div>
            <h1>قبل از جواب دادن، پیامش را رمزگشایی کن.</h1>
            <p>
              Message Decoder کمک می‌کند بفهمی پشت پیام‌های سرد، تند، مبهم یا کنایه‌آمیز چه نیازی پنهان است و
              چطور کم‌ریسک‌تر جواب بدهی.
            </p>
            <div className="trust">
              <span>بدون تشخیص روانشناختی.</span>
              <span>بدون برچسب‌زدن به شخصیت آدم‌ها.</span>
              <span>فقط تحلیل لحن، نیاز احتمالی، ریسک مکالمه و مسیر پاسخ.</span>
            </div>
          </div>

          <div className="workspace">
            <div className="grid">
              <label className="field">
                <span className="label">پیامی که گیجت کرده را وارد کن</span>
                <textarea
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="مثلاً: باشه، هر جور راحتی. معلومه برات مهم نیست."
                />
                <span className="hint">برای حفظ حریم خصوصی، اسم، شماره، آدرس یا اطلاعات حساس را حذف کن.</span>
              </label>

              <label className="field">
                <span className="label">نوع رابطه</span>
                <select value={relationship} onChange={(event) => setRelationship(event.target.value)}>
                  {relationshipOptions.map(([value, label]) => (
                    <option value={value} key={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span className="label">هدف تو از پاسخ</span>
                <select value={goal} onChange={(event) => setGoal(event.target.value)}>
                  {goalOptions.map(([value, label]) => (
                    <option value={value} key={value}>
                      {label}
                    </option>
                  ))}
                </select>
              </label>

              <label className="field">
                <span className="label">زمینه اختیاری</span>
                <input value={context} onChange={(event) => setContext(event.target.value)} placeholder="قبلش چه اتفاقی افتاد؟" />
              </label>

              <label className="field">
                <span className="label">تنظیمات داده</span>
                <select value={consent} onChange={(event) => setConsent(event.target.value as never)}>
                  <option value="none">پیام من ذخیره نشود.</option>
                  <option value="history">فقط برای تاریخچه خودم ذخیره شود.</option>
                  <option value="anonymized">ناشناس برای بهبود محصول استفاده شود.</option>
                </select>
              </label>

              <button className="primary" onClick={handleFreeDecode} disabled={!message.trim()}>
                <Sparkles size={18} /> تحلیل سریع رایگان
              </button>
            </div>

            {status ? <p className="success">{status}</p> : null}
            {error ? <p className="error">{error}</p> : null}

            {freeResult ? <FreeResult result={freeResult} /> : null}

            {freeResult ? (
              <div className="result">
                <div className="section">
                  <h3>این تحلیل چقدر نزدیک بود؟</h3>
                  <div className="actions">
                    {["خیلی دقیق بود", "نسبتاً درست بود", "نصفه‌نیمه بود", "اشتباه بود"].map((rating) => (
                      <button className="secondary" key={rating} onClick={() => handleFeedback(rating)}>
                        {rating}
                      </button>
                    ))}
                  </div>
                </div>
              </div>
            ) : null}

            {freeResult?.free_output ? (
              <div className="result">
                <div className="section paywall">
                  <h3>حالا پاسخ آماده بساز</h3>
                  <p>برای همین موقعیت، پاسخ‌های قابل کپی بساز: نرم، مرزبردار و کوتاه.</p>
                  <div className="actions" style={{ marginTop: 12 }}>
                    <input placeholder="شماره موبایل" value={phone} onChange={(event) => setPhone(event.target.value)} />
                    <input placeholder="کد OTP" value={otp} onChange={(event) => setOtp(event.target.value)} />
                    <button className="secondary" onClick={handleOtp}>دریافت کد</button>
                    <button className="secondary" onClick={handleVerify}>ورود</button>
                    <button className="secondary" onClick={handleBuyCredits}>
                      <CreditCard size={17} /> خرید ۵ کردیت sandbox
                    </button>
                    <button className="primary" onClick={handlePaidDecode}>استفاده از ۱ کردیت</button>
                  </div>
                </div>
              </div>
            ) : null}

            {paidResult ? (
              <div className="result">
                <div className="section">
                  <h3>تحلیل عمیق‌تر</h3>
                  <p>{paidResult.paid_output.deep_read}</p>
                </div>
                {paidResult.paid_output.reply_options.map((reply) => (
                  <div className="section reply" key={reply.label}>
                    <h3>{reply.label}</h3>
                    <blockquote>{reply.text}</blockquote>
                    <p>{reply.why_it_works}</p>
                    <button className="secondary" onClick={() => handleCopy(reply.text, reply.label)}>
                      <Clipboard size={17} /> کپی پاسخ
                    </button>
                  </div>
                ))}
                <div className="section">
                  <h3>کلمات ممنوع</h3>
                  <p>{paidResult.paid_output.words_to_avoid.join("، ")}</p>
                </div>
                <div className="section">
                  <h3>فرستادی؟ نتیجه چی شد؟</h3>
                  <div className="actions">
                    <button className="secondary" onClick={() => handleFeedback("paid", "تنش کمتر شد", 1)}>تنش کمتر شد</button>
                    <button className="secondary" onClick={() => handleFeedback("paid", "طرف بهتر توضیح داد", 1)}>طرف بهتر توضیح داد</button>
                    <button className="secondary" onClick={() => handleFeedback("paid", "دعوا بیشتر شد", 4)}>دعوا بیشتر شد</button>
                    <button className="secondary" onClick={() => handleFeedback("paid", "هنوز نفرستادم")}>هنوز نفرستادم</button>
                  </div>
                </div>
              </div>
            ) : null}
          </div>
        </section>
      </div>

      <footer className="footer-band">
        <div className="shell">این ابزار جایگزین مشاور، روان‌درمانگر یا کمک اضطراری نیست.</div>
      </footer>
    </main>
  );
}

function FreeResult({ result }: { result: FreeDecodeResponse }) {
  if (result.safety_output) {
    return (
      <div className="result">
        <div className="section">
          <span className="lens"><ShieldCheck size={16} /> {result.safety_output.warning_title}</span>
          <p style={{ marginTop: 10 }}>{result.safety_output.priority}</p>
        </div>
        <div className="section">
          <h3>پاسخ پیشنهادی کوتاه</h3>
          <p>{result.safety_output.suggested_reply}</p>
        </div>
        <div className="section">
          <h3>توصیه</h3>
          <p>{result.safety_output.recommendation}</p>
        </div>
      </div>
    );
  }

  const output = result.free_output;
  if (!output) return null;

  return (
    <div className="result">
      <div className="section">
        <span className="lens">
          {output.dominant_lens.fa} — {output.dominant_lens.en}
        </span>
        <p style={{ marginTop: 10 }}>{output.dominant_lens_explanation}</p>
      </div>
      <Info title="چرا این لنز دیده می‌شود؟" text={output.why_this_lens} />
      <Info title="برداشت احتمالی پشت پیام" text={output.likely_underlying_need} />
      <Info title="ریسک پاسخ اشتباه" text={output.conversation_risk} />
      <Info title="جهت بهتر پاسخ" text={output.recommended_direction} />
      <Info title={`احتمال خطا: ${output.confidence}`} text={output.alternative_read} />
      {output.privacy_warning ? <Info title="حریم خصوصی" text={output.privacy_warning} /> : null}
    </div>
  );
}

function Info({ title, text }: { title: string; text: string }) {
  return (
    <div className="section">
      <h3>{title}</h3>
      <p>{text}</p>
    </div>
  );
}
