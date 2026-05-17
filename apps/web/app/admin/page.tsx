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
    <main className="page">
      <div className="shell" style={{ paddingTop: 32 }}>
        <div className="topbar">
          <div className="brand">
            Admin
            <span>Message Decoder</span>
          </div>
        </div>
        <div className="workspace">
          <div className="grid">
            <label className="field">
              <span className="label">Admin Token</span>
              <input value={token} onChange={(event) => setToken(event.target.value)} placeholder="change-me-admin-token" />
            </label>
            <button className="primary" onClick={loadMetrics}>نمایش metrics</button>
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
              <div className="section">
                <h3>Lens mix</h3>
                <p>{metrics.by_lens.map((item) => `${item.dominant_lens}: ${item.count}`).join("، ") || "داده‌ای نیست"}</p>
              </div>
              <div className="section">
                <h3>Safety labels</h3>
                <p>{metrics.safety.map((item) => `${item.safety_label}: ${item.count}`).join("، ") || "داده‌ای نیست"}</p>
              </div>
            </div>
          ) : null}
        </div>
      </div>
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
