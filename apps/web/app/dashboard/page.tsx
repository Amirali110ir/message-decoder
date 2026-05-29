"use client";

import { AlertCircle, Check, Copy, History, MessageSquareText, RefreshCw, Sparkles, UserPlus, Zap } from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import { Contact, DecodeHistoryItem, getContacts, getCredits, getDecodeHistory, getReferral } from "../../lib/api";

type Referral = { referral_code: string; referral_url: string; reward_credits: number };

export default function DashboardPage() {
  const [token, setToken] = useState("");
  const [phone, setPhone] = useState("");
  const [credits, setCredits] = useState<number | null>(null);
  const [referral, setReferral] = useState<Referral | null>(null);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [history, setHistory] = useState<DecodeHistoryItem[]>([]);
  const [hydrated, setHydrated] = useState(false);
  const [loading, setLoading] = useState(true);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");

  useEffect(() => {
    const savedToken = window.localStorage.getItem("message-decoder-token") || "";
    const savedPhone = window.localStorage.getItem("message-decoder-phone") || "";
    setHydrated(true);
    setToken(savedToken);
    setPhone(savedPhone);
    if (savedToken) void loadDashboard(savedToken);
    else setLoading(false);
  }, []);

  async function loadDashboard(authToken = token) {
    setLoading(true);
    setError("");
    try {
      const [creditResult, referralResult, contactResult, historyResult] = await Promise.all([
        getCredits(authToken),
        getReferral(authToken),
        getContacts(authToken),
        getDecodeHistory(authToken)
      ]);
      setCredits(creditResult.credit_balance);
      setReferral(referralResult);
      setContacts(contactResult);
      setHistory(historyResult.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "داشبورد لود نشد. دوباره وارد شوید.");
    } finally {
      setLoading(false);
    }
  }

  async function copyReferral() {
    if (!referral) return;
    await navigator.clipboard.writeText(referral.referral_url);
    setStatus("لینک معرفی کپی شد.");
  }

  function logout() {
    window.localStorage.removeItem("message-decoder-token");
    window.localStorage.removeItem("message-decoder-phone");
    setToken("");
    setCredits(null);
    setReferral(null);
    setContacts([]);
    setHistory([]);
  }

  return (
    <main className="page decoder-page">
      <header className="topbar">
        <div className="shell topbar-inner">
          <Link className="brand" href="/" aria-label="Message Decoder">
            <div className="brand-logo"><MessageSquareText size={20} /></div>
            <div className="brand-text">
              <span className="brand-title">Message Decoder</span>
              <span className="brand-subtitle">داشبورد حساب</span>
            </div>
          </Link>
          <div className="nav-actions">
            <Link className="nav-login" href="/decoder">تحلیل جدید</Link>
            {token ? <button className="nav-login" onClick={logout}>خروج</button> : <Link className="nav-cta" href="/signup">ثبت‌نام</Link>}
          </div>
        </div>
      </header>

      <section className="decoder-section dashboard-section">
        <div className="shell workspace">
          <div className="section-heading">
            <span>حساب کاربری</span>
            <h1>اعتبار، تاریخچه، مخاطب‌ها و کد معرفی شما</h1>
            <p>از اینجا می‌توانید وضعیت حساب را ببینید و برای تحلیل بعدی به وب یا تلگرام بروید.</p>
          </div>

          {status && <div className="toast-msg toast-success"><Check size={16} /><span>{status}</span></div>}
          {error && <div className="toast-msg toast-error"><AlertCircle size={16} /><span>{error}</span></div>}

          {!hydrated ? (
            <div className="panel-card signup-card">
              <h2>در حال آماده‌سازی داشبورد...</h2>
              <p>اگر قبلاً وارد شده باشید، اطلاعات حساب همین‌جا نمایش داده می‌شود.</p>
            </div>
          ) : !token && !loading ? (
            <div className="panel-card signup-card dashboard-empty-card">
              <h2>داشبورد بعد از اولین تحلیل معنا پیدا می‌کند</h2>
              <p>اینجا بعد از ورود، اعتبار، تاریخچه تحلیل‌ها، مخاطب‌های ذخیره‌شده و کد معرفی شما نمایش داده می‌شود.</p>
              <div className="auth-actions-group">
                <Link className="btn-primary" href="/decoder">تحلیل پیام اول</Link>
                <Link className="btn-secondary" href="/signup">ورود / ثبت‌نام</Link>
              </div>
            </div>
          ) : (
            <>
              <div className="result">
                <div className="section">
                  <h3>شماره حساب</h3>
                  <p>{phone || "ثبت شده"}</p>
                </div>
                <div className="section">
                  <h3>اعتبار فعلی</h3>
                  <p>{loading ? "..." : `${credits ?? 0} اعتبار`}</p>
                </div>
                <div className="section">
                  <h3>تحلیل‌های ذخیره‌شده</h3>
                  <p>{history.length}</p>
                </div>
                <div className="section">
                  <h3>مخاطب‌ها</h3>
                  <p>{contacts.length}</p>
                </div>
              </div>

              <div className="dashboard-grid">
                <div className="panel-card">
                  <div className="panel-title">
                    <UserPlus size={19} />
                    <div>
                      <h3>برنامه معرفی</h3>
                      <p>هر شماره جدیدی که با کد شما ثبت‌نام کند، ۵ اعتبار برای شما فعال می‌شود.</p>
                    </div>
                  </div>
                  {referral ? (
                    <div className="referral-box">
                      <strong>{referral.referral_code}</strong>
                      <span>{referral.referral_url}</span>
                      <button className="btn-secondary" onClick={copyReferral}><Copy size={15} /> کپی لینک معرفی</button>
                    </div>
                  ) : (
                    <button className="btn-secondary" onClick={() => loadDashboard()} disabled={loading}>
                      <RefreshCw className={loading ? "animate-spin" : ""} size={15} />
                      دریافت کد معرفی
                    </button>
                  )}
                </div>

                <div className="panel-card">
                  <div className="panel-title">
                    <Zap size={19} />
                    <div>
                      <h3>مسیر بعدی</h3>
                      <p>پیام بعدی را در وب تحلیل کنید یا مستقیم داخل بات تلگرام بفرستید.</p>
                    </div>
                  </div>
                  <div className="auth-actions-group">
                    <Link className="btn-primary" href="/decoder"><Sparkles size={16} /> تحلیل پیام جدید</Link>
                    <a className="btn-secondary" href="https://t.me/MeDecoderBot" target="_blank" rel="noreferrer">رفتن به تلگرام</a>
                  </div>
                </div>
              </div>

              <div className="panel-card">
                <div className="admin-list-heading">
                  <div>
                    <span className="label">History</span>
                    <h2>آخرین تحلیل‌های ذخیره‌شده</h2>
                  </div>
                  <button className="mini-action" onClick={() => loadDashboard()} disabled={loading}>
                    <RefreshCw className={loading ? "animate-spin" : ""} size={14} />
                    به‌روزرسانی
                  </button>
                </div>
                {history.length ? (
                  <div className="history-list">
                    {history.slice(0, 8).map((item) => (
                      <div className="history-row" key={item.id}>
                        <div className="history-row-main">
                          <strong>{item.relationship_type} · {item.dominant_lens}</strong>
                          <span>{item.message_preview || "پیام بدون متن ذخیره شده است."}</span>
                        </div>
                        <span className="admin-pill">{item.has_paid_output ? "paid" : "free"}</span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="contact-empty-note">
                    هنوز تاریخچه‌ای ندارید. در صفحه تحلیل، حریم خصوصی را روی «تاریخچه حساب من» بگذارید تا تحلیل‌ها اینجا نمایش داده شوند.
                  </div>
                )}
              </div>

              <div className="panel-card">
                <div className="panel-title">
                  <History size={19} />
                  <div>
                    <h3>مخاطب‌های ذخیره‌شده</h3>
                    <p>مخاطب‌ها برای دماسنج رابطه و دقیق‌تر شدن تحلیل‌های بعدی استفاده می‌شوند.</p>
                  </div>
                </div>
                {contacts.length ? (
                  <div className="history-list">
                    {contacts.slice(0, 8).map((contact) => (
                      <div className="history-row" key={contact.id}>
                        <div className="history-row-main">
                          <strong>{contact.name} · {contact.relationship_type}</strong>
                          <span>{contact.memory_summary || contact.profile_summary || `${contact.interaction_count} تحلیل ذخیره‌شده`}</span>
                        </div>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="contact-empty-note">هنوز مخاطبی ساخته نشده است.</div>
                )}
              </div>
            </>
          )}
        </div>
      </section>
    </main>
  );
}
