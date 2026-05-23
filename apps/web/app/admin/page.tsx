"use client";

import { useState } from "react";
import { RefreshCw, Search } from "lucide-react";
import { adminDecodeList, adminMetrics } from "../../lib/api";

type Metrics = Awaited<ReturnType<typeof adminMetrics>>;
type DecodeList = Awaited<ReturnType<typeof adminDecodeList>>;

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [decodes, setDecodes] = useState<DecodeList | null>(null);
  const [relationshipType, setRelationshipType] = useState("");
  const [dominantLens, setDominantLens] = useState("");
  const [safetyLabel, setSafetyLabel] = useState("");
  const [promptVersion, setPromptVersion] = useState("");
  const [loading, setLoading] = useState(false);
  const [error, setError] = useState("");

  async function loadDashboard() {
    setError("");
    setLoading(true);
    try {
      const filters = {
        relationship_type: relationshipType,
        dominant_lens: dominantLens,
        safety_label: safetyLabel,
        prompt_version: promptVersion,
        limit: 50
      };
      const [metricsResult, decodeResult] = await Promise.all([
        adminMetrics(token),
        adminDecodeList(token, filters)
      ]);
      setMetrics(metricsResult);
      setDecodes(decodeResult);
    } catch (err) {
      setError(err instanceof Error ? err.message : "داده‌های داشبورد دریافت نشد.");
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="page admin-page">
      <header className="topbar">
        <div className="shell topbar-inner">
          <div className="brand">
            <div className="brand-logo">A</div>
            <div className="brand-text">
              <span className="brand-title">Admin</span>
              <span className="brand-subtitle">Message Decoder</span>
            </div>
          </div>
          <a className="nav-login" href="/">
            صفحه اصلی
          </a>
        </div>
      </header>

      <section className="admin-section">
        <div className="shell workspace">
          <div className="section-heading">
            <span>داشبورد داخلی</span>
            <h1>شاخص‌های رشد و کیفیت پاسخ‌ها</h1>
            <p>توکن ادمین را وارد کنید تا استفاده، تبدیل، نرخ کپی و کیفیت خروجی‌ها را در یک نگاه ببینید.</p>
          </div>

          <div className="panel-card">
            <div className="admin-toolbar">
              <label className="field">
                <span className="label">Admin Token</span>
                <input value={token} onChange={(event) => setToken(event.target.value)} placeholder="change-me-admin-token" />
              </label>
              <label className="field">
                <span className="label">نوع رابطه</span>
                <select value={relationshipType} onChange={(event) => setRelationshipType(event.target.value)}>
                  <option value="">همه</option>
                  <option value="romantic">رابطه عاطفی</option>
                  <option value="ex">اکس</option>
                  <option value="friend">دوست</option>
                  <option value="family">خانواده</option>
                  <option value="manager_colleague">مدیر یا همکار</option>
                  <option value="customer">مشتری</option>
                  <option value="unknown">نامشخص</option>
                </select>
              </label>
              <label className="field">
                <span className="label">لنز غالب</span>
                <select value={dominantLens} onChange={(event) => setDominantLens(event.target.value)}>
                  <option value="">همه</option>
                  <option value="dopamine">هدف و کنترل</option>
                  <option value="oxytocin">امنیت و اعتماد</option>
                  <option value="serotonin">شأن و احترام</option>
                </select>
              </label>
              <label className="field">
                <span className="label">Safety</span>
                <select value={safetyLabel} onChange={(event) => setSafetyLabel(event.target.value)}>
                  <option value="">همه</option>
                  <option value="normal">normal</option>
                  <option value="watch">watch</option>
                  <option value="high_risk">high_risk</option>
                </select>
              </label>
              <label className="field">
                <span className="label">Prompt version</span>
                <input value={promptVersion} onChange={(event) => setPromptVersion(event.target.value)} placeholder="message-decoder-system-v0.2" />
              </label>
              <button className="primary admin-load-button" onClick={loadDashboard} disabled={loading}>
                {loading ? <RefreshCw className="animate-spin" size={16} /> : <Search size={16} />}
                <span>بارگذاری داشبورد</span>
              </button>
            </div>
          </div>

          {error ? <p className="error">{error}</p> : null}

          {metrics ? (
            <div className="result">
              <Metric title="کاربران" value={metrics.users} />
              <Metric title="تحلیل‌های رایگان" value={metrics.free_decodes} />
              <Metric title="تحلیل‌های کامل" value={metrics.paid_decodes} />
              <Metric title="Revenue" value={metrics.revenue} />
              <Metric title="نرخ تبدیل" value={`${Math.round(metrics.conversion * 100)}٪`} />
              <Metric title="نرخ کپی پاسخ" value={`${Math.round(metrics.copy_rate * 100)}٪`} />
              <Metric title="ترکیب لنزها" value={metrics.by_lens.map((item) => `${item.dominant_lens}: ${item.count}`).join("، ") || "هنوز داده‌ای نیست"} />
              <Metric title="برچسب‌های ایمنی" value={metrics.safety.map((item) => `${item.safety_label}: ${item.count}`).join("، ") || "هنوز داده‌ای نیست"} />
            </div>
          ) : null}

          {decodes ? (
            <div className="panel-card">
              <div className="admin-list-heading">
                <div>
                  <span className="label">Decode listing</span>
                  <h2>نمای ناشناس تحلیل‌ها</h2>
                </div>
                <span>{decodes.total} مورد</span>
              </div>
              <div className="admin-table-wrap">
                <table className="admin-table">
                  <thead>
                    <tr>
                      <th>زمان</th>
                      <th>رابطه</th>
                      <th>لنز</th>
                      <th>Safety</th>
                      <th>Prompt</th>
                      <th>Preview</th>
                      <th>Signals</th>
                    </tr>
                  </thead>
                  <tbody>
                    {decodes.items.map((item) => (
                      <tr key={item.id}>
                        <td>{formatDate(item.created_at)}</td>
                        <td>{relationshipLabel(item.relationship_type)}</td>
                        <td>{lensLabel(item.dominant_lens)}</td>
                        <td><span className={`admin-pill ${item.safety_label}`}>{item.safety_label}</span></td>
                        <td>{item.prompt_version}</td>
                        <td>{item.anonymized_preview || "پیام ذخیره نشده"}</td>
                        <td>
                          <div className="admin-badges">
                            <span>{item.has_paid_output ? "paid" : "free"}</span>
                            <span>{item.copy_count} copy</span>
                            <span>{item.feedback_count} feedback</span>
                          </div>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            </div>
          ) : null}
        </div>
      </section>
    </main>
  );
}

function Metric({ title, value }: { title: string; value: string | number }) {
  return (
    <div className="section">
      <h3>{title}</h3>
      <p>{value}</p>
    </div>
  );
}

function formatDate(value: string) {
  return new Intl.DateTimeFormat("fa-IR", {
    dateStyle: "short",
    timeStyle: "short"
  }).format(new Date(value));
}

function relationshipLabel(value: string) {
  return ({
    romantic: "عاطفی",
    ex: "اکس",
    friend: "دوست",
    family: "خانواده",
    manager_colleague: "کار",
    customer: "مشتری",
    unknown: "نامشخص"
  } as Record<string, string>)[value] ?? value;
}

function lensLabel(value: string) {
  return ({
    dopamine: "هدف و کنترل",
    oxytocin: "امنیت و اعتماد",
    serotonin: "شأن و احترام"
  } as Record<string, string>)[value] ?? value;
}
