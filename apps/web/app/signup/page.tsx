"use client";

import { AlertCircle, Check, KeyRound, LogIn, MessageSquareText, Send, Sparkles } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { notifyTelegramOtp, requestOtp, verifyOtpWithReferral } from "../../lib/api";

export default function SignupPage() {
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [referralCode, setReferralCode] = useState("");
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const params = new URLSearchParams(window.location.search);
    const ref = params.get("ref") || params.get("referral") || "";
    if (ref) setReferralCode(ref.toUpperCase());
  }, []);

  async function sendOtp() {
    if (!phone.trim()) {
      setError("شماره موبایل را با فرمت 09123456789 وارد کنید.");
      return;
    }
    setError("");
    setStatus("");
    setLoading(true);
    try {
      const result = await requestOtp(phone);
      await notifyTelegramOtp(result.telegram_payload);
      setOtpSent(true);
      setStatus(result.dev_otp_code
        ? `نسخه تست: کد ورود ${result.dev_otp_code} است.`
        : "کد ورود ارسال شد. اگر همین شماره در تلگرام وصل باشد، کد داخل بات هم می‌آید.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "کد ورود ارسال نشد.");
    } finally {
      setLoading(false);
    }
  }

  async function verify() {
    if (!otp.trim()) {
      setError("کد ورود را وارد کنید.");
      return;
    }
    setError("");
    setStatus("");
    setLoading(true);
    try {
      const result = await verifyOtpWithReferral(phone, otp, referralCode || undefined);
      window.localStorage.setItem("message-decoder-token", result.token);
      window.localStorage.setItem("message-decoder-phone", phone);
      setStatus(`حساب آماده شد. اعتبار فعلی شما ${result.credit_balance} است.`);
      window.location.assign("/dashboard");
    } catch (err) {
      setError(err instanceof Error ? err.message : "کد ورود درست نیست یا منقضی شده است.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page decoder-page">
      <header className="topbar">
        <div className="shell topbar-inner">
          <Link className="brand" href="/" aria-label="Message Decoder">
            <div className="brand-logo"><MessageSquareText size={20} /></div>
            <div className="brand-text">
              <span className="brand-title">Message Decoder</span>
              <span className="brand-subtitle">ثبت‌نام و ورود</span>
            </div>
          </Link>
          <div className="nav-actions">
            <Link className="nav-login" href="/decoder">تحلیل رایگان</Link>
            <a className="nav-login" href="https://t.me/MeDecoderBot" target="_blank" rel="noreferrer">تلگرام</a>
          </div>
        </div>
      </header>

      <section className="decoder-section onboarding-section">
        <div className="shell onboarding-layout">
          <div className="onboarding-copy">
            <span className="eyebrow">ورود بعد از تحلیل</span>
            <h1>برای ساخت پاسخ کامل، تاریخچه و کد معرفی وارد شوید.</h1>
            <p>تحلیل اولیه بدون ورود انجام می‌شود. حساب فقط وقتی لازم است که بخواهید پاسخ‌های قابل ارسال بسازید، تحلیل‌ها را ذخیره کنید یا ۵ اعتبار هدیه را بگیرید.</p>
            <div className="onboarding-steps">
              <div><strong>۱</strong><span>اگر هنوز تحلیل نگرفته‌اید، از تحلیل رایگان شروع کنید.</span></div>
              <div><strong>۲</strong><span>برای پاسخ کامل، شماره را وارد کنید و کد ورود بگیرید.</span></div>
              <div><strong>۳</strong><span>بعد از ورود، اعتبار، تاریخچه، مخاطب‌ها و کد معرفی فعال می‌شوند.</span></div>
            </div>
          </div>

          <div className="panel-card signup-card">
            <div className="panel-title">
              <KeyRound size={19} />
              <div>
                <h3>ورود یا ثبت‌نام</h3>
                <p>اگر قبلاً حساب داشته باشید، همین مسیر شما را وارد حساب قبلی می‌کند.</p>
              </div>
            </div>

            {status && <div className="toast-msg toast-success"><Check size={16} /><span>{status}</span></div>}
            {error && <div className="toast-msg toast-error"><AlertCircle size={16} /><span>{error}</span></div>}

            <div className="auth-grid">
              <div className="field-group">
                <label className="field-label">شماره موبایل</label>
                <input type="tel" inputMode="tel" autoComplete="tel" placeholder="09123456789" value={phone} onChange={(event) => setPhone(event.target.value)} />
              </div>
              <button className="btn-secondary" onClick={sendOtp} disabled={loading}>
                <Send size={15} />
                <span>گرفتن کد ورود</span>
              </button>
              {otpSent && (
                <>
                  <div className="field-group">
                    <label className="field-label">کد ورود</label>
                    <input type="text" inputMode="numeric" autoComplete="one-time-code" placeholder="کد ۶ رقمی" value={otp} onChange={(event) => setOtp(event.target.value)} />
                  </div>
                  <div className="field-group">
                    <label className="field-label">کد معرفی اختیاری</label>
                    <input type="text" placeholder="مثلاً ABCD1234" value={referralCode} onChange={(event) => setReferralCode(event.target.value.toUpperCase())} />
                  </div>
                  <button className="btn-primary" onClick={verify} disabled={loading}>
                    <LogIn size={16} />
                    <span>ورود و فعال‌سازی حساب</span>
                  </button>
                </>
              )}
            </div>

            <div className="contact-empty-note">
              اگر شماره‌تان را در بات تلگرام تایید کرده باشید، کد ورود همان‌جا هم ارسال می‌شود.
            </div>
            <Link className="auth-free-link" href="/decoder">
              <Sparkles size={15} />
              <span>اول تحلیل رایگان را ببینم</span>
            </Link>
          </div>
        </div>
      </section>
    </main>
  );
}
