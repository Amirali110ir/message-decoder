"use client";

import { useState } from "react";
import { adminMetrics } from "../../lib/api";

type Metrics = Awaited<ReturnType<typeof adminMetrics>>;

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [error, setError] = useState("");

  async function loadMetrics() {
    setError("");
    try {
      setMetrics(await adminMetrics(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "خطا در دریافت داشبورد");
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
            بازگشت به سایت
          </a>
        </div>
      </header>

      <section className="admin-section">
        <div className="shell workspace">
          <div className="section-heading">
            <span>داشبورد داخلی</span>
            <h1>Metrics محصول</h1>
            <p>توکن ادمین را وارد کنید تا شاخص‌های استفاده، تبدیل و کیفیت پاسخ‌ها را ببینید.</p>
          </div>

          <div className="panel-card">
            <div className="grid">
              <label className="field">
                <span className="label">Admin Token</span>
                <input value={token} onChange={(event) => setToken(event.target.value)} placeholder="change-me-admin-token" />
              </label>
              <button className="primary" onClick={loadMetrics}>نمایش metrics</button>
            </div>
          </div>

          {error ? <p className="error">{error}</p> : null}

          {metrics ? (
            <div className="result">
              <Metric title="Users" value={metrics.users} />
              <Metric title="Free decodes" value={metrics.free_decodes} />
              <Metric title="Paid decodes" value={metrics.paid_decodes} />
              <Metric title="Revenue" value={metrics.revenue} />
              <Metric title="Conversion" value={`${Math.round(metrics.conversion * 100)}٪`} />
              <Metric title="Copy rate" value={`${Math.round(metrics.copy_rate * 100)}٪`} />
              <Metric title="Lens mix" value={metrics.by_lens.map((item) => `${item.dominant_lens}: ${item.count}`).join("، ") || "داده‌ای نیست"} />
              <Metric title="Safety labels" value={metrics.safety.map((item) => `${item.safety_label}: ${item.count}`).join("، ") || "داده‌ای نیست"} />
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
