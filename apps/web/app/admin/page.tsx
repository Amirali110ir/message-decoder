"use client";

import { useState } from "react";
import { LockKeyhole, LogIn, LogOut, MinusCircle, PlusCircle, RefreshCw, Search, Send } from "lucide-react";
import {
  adminActivityList,
  adminLogin,
  adminDecodeList,
  adminGrantAllCredits,
  adminGrantCredits,
  adminMetrics,
  adminUserList,
  telegramAdminMetrics,
  telegramAdminActivity,
  telegramAdminUsers,
  telegramBroadcast,
  TelegramBroadcastResult,
  telegramGrantAllCredits,
  telegramGrantCredits
} from "../../lib/api";

type Metrics = Awaited<ReturnType<typeof adminMetrics>>;
type DecodeList = Awaited<ReturnType<typeof adminDecodeList>>;
type UserList = Awaited<ReturnType<typeof adminUserList>>;
type ActivityList = Awaited<ReturnType<typeof adminActivityList>>;
type TelegramMetrics = Awaited<ReturnType<typeof telegramAdminMetrics>>;
type TelegramUsers = Awaited<ReturnType<typeof telegramAdminUsers>>;
type TelegramActivityList = Awaited<ReturnType<typeof telegramAdminActivity>>;

const defaultReleaseNote = `آپدیت جدید Message Decoder

تلگرام فعال شد و حالا می‌توانید پیام‌ها را مستقیم داخل بات تحلیل کنید.

تازه‌ها:
- ۵ اعتبار هدیه برای کاربران فعال می‌شود.
- با /referral کد معرفی اختصاصی می‌گیرید.
- هر شماره جدیدی که با کد شما ثبت‌نام کند، ۵ اعتبار برای شما فعال می‌شود.
- تحلیل‌ها با هوش مصنوعی دقیق‌تر شده‌اند.
- واتس‌اپ به‌زودی اضافه می‌شود.

برای شروع پیامتان را بفرستید و نوع رابطه و هدف پاسخ را انتخاب کنید.`;

export default function AdminPage() {
  const [token, setToken] = useState("");
  const [adminPhone, setAdminPhone] = useState("");
  const [adminPassword, setAdminPassword] = useState("");
  const [metrics, setMetrics] = useState<Metrics | null>(null);
  const [telegramMetrics, setTelegramMetrics] = useState<TelegramMetrics | null>(null);
  const [decodes, setDecodes] = useState<DecodeList | null>(null);
  const [users, setUsers] = useState<UserList | null>(null);
  const [activities, setActivities] = useState<ActivityList | null>(null);
  const [telegramUsers, setTelegramUsers] = useState<TelegramUsers | null>(null);
  const [telegramActivities, setTelegramActivities] = useState<TelegramActivityList | null>(null);
  const [broadcastResults, setBroadcastResults] = useState<TelegramBroadcastResult[]>([]);
  const [relationshipType, setRelationshipType] = useState("");
  const [dominantLens, setDominantLens] = useState("");
  const [safetyLabel, setSafetyLabel] = useState("");
  const [promptVersion, setPromptVersion] = useState("");
  const [userQuery, setUserQuery] = useState("");
  const [grantPhone, setGrantPhone] = useState("");
  const [grantAmount, setGrantAmount] = useState(5);
  const [releaseNote, setReleaseNote] = useState(defaultReleaseNote);
  const [loading, setLoading] = useState(false);
  const [actionStatus, setActionStatus] = useState("");
  const [error, setError] = useState("");

  async function login() {
    setError("");
    setActionStatus("");
    setLoading(true);
    try {
      const result = await adminLogin(adminPhone, adminPassword);
      setToken(result.token);
      setAdminPassword("");
      setActionStatus("ورود ادمین انجام شد.");
      await loadDashboardWithToken(result.token);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ورود ادمین انجام نشد.");
    } finally {
      setLoading(false);
    }
  }

  function logout() {
    setToken("");
    setAdminPassword("");
    setMetrics(null);
    setTelegramMetrics(null);
    setDecodes(null);
    setUsers(null);
    setActivities(null);
    setTelegramUsers(null);
    setTelegramActivities(null);
    setBroadcastResults([]);
  }

  async function loadDashboard() {
    await loadDashboardWithToken(token);
  }

  async function loadDashboardWithToken(activeToken: string) {
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
      const results = await Promise.allSettled([
        adminMetrics(activeToken),
        adminDecodeList(activeToken, filters),
        adminUserList(activeToken, { q: userQuery, limit: 100 }),
        adminActivityList(activeToken, { q: userQuery, limit: 80 }),
        telegramAdminUsers(activeToken, userQuery),
        telegramAdminMetrics(activeToken),
        telegramAdminActivity(activeToken, userQuery)
      ]);
      const labels = ["شاخص‌های وب", "تحلیل‌های وب", "کاربران وب", "اتفاقات وب", "کاربران تلگرام", "شاخص‌های تلگرام", "اتفاقات تلگرام"];
      const failures: string[] = [];
      results.forEach((result, index) => {
        if (result.status === "rejected") failures.push(labels[index]);
      });
      if (results[0].status === "fulfilled") setMetrics(results[0].value);
      if (results[1].status === "fulfilled") setDecodes(results[1].value);
      if (results[2].status === "fulfilled") setUsers(results[2].value);
      if (results[3].status === "fulfilled") setActivities(results[3].value);
      if (results[4].status === "fulfilled") setTelegramUsers(results[4].value);
      if (results[5].status === "fulfilled") setTelegramMetrics(results[5].value);
      if (results[6].status === "fulfilled") setTelegramActivities(results[6].value);
      if (failures.length) {
        setError(`بخشی از داشبورد لود نشد: ${failures.join("، ")}. بخش‌های دیگر قابل استفاده‌اند.`);
      }
    } catch (err) {
      setError(err instanceof Error ? err.message : "داده‌های داشبورد دریافت نشد.");
    } finally {
      setLoading(false);
    }
  }

  async function adjustCredits(phone: string, amount: number) {
    const verb = amount > 0 ? "اضافه" : "کم";
    if (!window.confirm(`برای شماره ${phone}، ${Math.abs(amount)} اعتبار ${verb} شود؟`)) return;
    setError("");
    setActionStatus("");
    try {
      await Promise.allSettled([
        adminGrantCredits(token, { phone, credits: amount }),
        telegramGrantCredits(token, { phone, credits: amount })
      ]);
      setActionStatus(`${amount} اعتبار برای شماره ${phone} اعمال شد، اگر در یکی از دیتابیس‌ها وجود داشته باشد.`);
      await loadDashboard();
    } catch (err) {
      setError(err instanceof Error ? err.message : "اعتبار اعمال نشد.");
    }
  }

  async function grantToPhone() {
    await adjustCredits(grantPhone, grantAmount);
  }

  async function grantFiveToAll() {
    if (!window.confirm("۵ اعتبار به همه کاربران وب و تلگرام اضافه شود؟ این عملیات همگانی است.")) return;
    setError("");
    setActionStatus("");
    const [apiResult, telegramResult] = await Promise.allSettled([
      adminGrantAllCredits(token, 5),
      telegramGrantAllCredits(token, 5)
    ]);
    const apiCount = apiResult.status === "fulfilled" ? apiResult.value.updated_users : 0;
    const telegramCount = telegramResult.status === "fulfilled" ? telegramResult.value.updated_users : 0;
    setActionStatus(`۵ اعتبار همگانی اعمال شد: وب ${apiCount} کاربر، تلگرام ${telegramCount} کاربر.`);
    await loadDashboard();
  }

  async function sendReleaseNote() {
    if (!window.confirm("این پیام برای همه کاربران تلگرام ارسال شود؟")) return;
    setError("");
    setActionStatus("");
    try {
      const result = await telegramBroadcast(token, releaseNote);
      setBroadcastResults(result.results ?? []);
      setActionStatus(`ریلیس نوت ارسال شد: ${result.sent} موفق، ${result.failed} ناموفق.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "ریلیس نوت ارسال نشد.");
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

      {!token ? (
        <section className="admin-login-section">
          <form className="admin-login-card" onSubmit={(event) => { event.preventDefault(); void login(); }}>
            <div className="admin-login-icon">
              <LockKeyhole size={24} />
            </div>
            <div className="admin-login-copy">
              <span>ورود امن ادمین</span>
              <h1>برای مشاهده داشبورد وارد شوید</h1>
              <p>اطلاعات کاربران، اعتبارها و broadcast فقط بعد از ورود نمایش داده می‌شود.</p>
            </div>
            <label className="field">
              <span className="label">شماره ادمین</span>
              <input value={adminPhone} onChange={(event) => setAdminPhone(event.target.value)} inputMode="tel" autoComplete="username" placeholder="شماره موبایل" />
            </label>
            <label className="field">
              <span className="label">رمز عبور</span>
              <input type="password" value={adminPassword} onChange={(event) => setAdminPassword(event.target.value)} autoComplete="current-password" placeholder="رمز عبور" />
            </label>
            {error ? <p className="error">{error}</p> : null}
            <button className="primary admin-load-button" type="submit" disabled={loading || !adminPhone || !adminPassword}>
              {loading ? <RefreshCw className="animate-spin" size={16} /> : <LogIn size={16} />}
              <span>ورود</span>
            </button>
          </form>
        </section>
      ) : (
      <section className="admin-section">
        <div className="shell workspace">
          <div className="section-heading">
            <span>داشبورد داخلی</span>
            <h1>شاخص‌های رشد و کیفیت پاسخ‌ها</h1>
            <p>با شماره ادمین وارد شوید تا کاربران وب و تلگرام، اعتبارها، پرداخت‌ها، معرفی‌ها و پیام‌های عمومی را کنترل کنید.</p>
          </div>

          <div className="panel-card">
            <div className="admin-toolbar">
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
              <label className="field">
                <span className="label">جستجوی کاربر/شماره</span>
                <input value={userQuery} onChange={(event) => setUserQuery(event.target.value)} placeholder="0912 یا کد معرفی" />
              </label>
              <button className="primary admin-load-button" onClick={loadDashboard} disabled={loading}>
                {loading ? <RefreshCw className="animate-spin" size={16} /> : <Search size={16} />}
                <span>بارگذاری داشبورد</span>
              </button>
              <button className="secondary admin-load-button" onClick={logout}>
                <LogOut size={16} />
                <span>خروج امن</span>
              </button>
            </div>
          </div>

          {error ? <p className="error">{error}</p> : null}
          {actionStatus ? <p className="success">{actionStatus}</p> : null}

          <div className="panel-card">
            <div className="admin-list-heading">
              <div>
                <span className="label">Credits & Release</span>
                <h2>اعتبار، معرفی و ارسال ریلیس نوت</h2>
              </div>
              <button className="primary" onClick={grantFiveToAll} disabled={!token}>
                <PlusCircle size={16} />
                <span>۵ اعتبار برای همه</span>
              </button>
            </div>
            <div className="admin-toolbar">
              <label className="field">
                <span className="label">شماره برای اعتبار دستی</span>
                <input value={grantPhone} onChange={(event) => setGrantPhone(event.target.value)} placeholder="09123456789" />
              </label>
              <label className="field">
                <span className="label">تعداد اعتبار</span>
                <input type="number" value={grantAmount} onChange={(event) => setGrantAmount(Number(event.target.value))} />
              </label>
              <button className="primary admin-load-button" onClick={grantToPhone} disabled={!token || !grantPhone}>
                <PlusCircle size={16} />
                <span>اعمال اعتبار</span>
              </button>
            </div>
            <label className="field">
              <span className="label">متن ریلیس نوت تلگرام</span>
              <textarea value={releaseNote} onChange={(event) => setReleaseNote(event.target.value)} rows={9} />
            </label>
            <button className="primary admin-load-button" onClick={sendReleaseNote} disabled={!token || !releaseNote.trim()}>
              <Send size={16} />
              <span>ارسال برای کاربران تلگرام</span>
            </button>
          </div>

          {broadcastResults.length ? (
            <BroadcastResultTable items={broadcastResults} />
          ) : null}

          {metrics ? (
            <div className="result">
              <Metric title="کاربران وب" value={metrics.users} />
              <Metric title="کاربران تلگرام" value={telegramMetrics?.users ?? 0} />
              <Metric title="اعتبارهای وب" value={metrics.total_credits ?? 0} />
              <Metric title="اعتبارهای تلگرام" value={telegramMetrics?.total_credits ?? 0} />
              <Metric title="معرفی‌های وب" value={metrics.referrals ?? 0} />
              <Metric title="معرفی‌های تلگرام" value={telegramMetrics?.referrals ?? 0} />
              <Metric title="مخاطب‌ها" value={metrics.contacts ?? 0} />
              <Metric title="پرداخت‌های موفق" value={metrics.verified_payments ?? 0} />
              <Metric title="درآمد ثبت‌شده" value={metrics.revenue} />
              <Metric title="پیامک‌های موفق" value={metrics.sms_sent ?? 0} />
              <Metric title="پیامک‌های ناموفق" value={metrics.sms_failed ?? 0} />
              <Metric title="تحلیل رایگان وب" value={metrics.free_decodes} />
              <Metric title="تحلیل کامل وب" value={metrics.paid_decodes} />
              <Metric title="تحلیل تلگرام" value={telegramMetrics?.free_decodes ?? 0} />
              <Metric title="نرخ تبدیل" value={`${Math.round(metrics.conversion * 100)}٪`} />
              <Metric title="نرخ کپی پاسخ" value={`${Math.round(metrics.copy_rate * 100)}٪`} />
              <Metric
                title="ماندگاری D7"
                value={`${Math.round((metrics.retention?.d7_retention.rate ?? 0) * 100)}٪ (${metrics.retention?.d7_retention.retained ?? 0}/${metrics.retention?.d7_retention.cohort ?? 0})`}
              />
              <Metric
                title="نرخ بازگشت هفتگی"
                value={`${Math.round((metrics.retention?.weekly_return.rate ?? 0) * 100)}٪ (${metrics.retention?.weekly_return.returned ?? 0}/${metrics.retention?.weekly_return.cohort ?? 0})`}
              />
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

          {users ? (
            <UserTable title="کاربران وب/API" items={users.items} onAdjust={adjustCredits} />
          ) : null}

          {telegramUsers ? (
            <TelegramUserTable title="کاربران تلگرام" items={telegramUsers.items} onAdjust={adjustCredits} />
          ) : null}

          {activities ? (
            <ActivityTable title="اتفاقات کاربران وب/API" source="Web/API" items={activities.items} />
          ) : null}

          {telegramActivities ? (
            <ActivityTable title="اتفاقات کاربران تلگرام" source="Telegram D1" items={telegramActivities.items} />
          ) : null}
        </div>
      </section>
      )}
    </main>
  );
}

function UserTable({ title, items, onAdjust }: { title: string; items: UserList["items"]; onAdjust: (phone: string, amount: number) => void }) {
  return (
    <div className="panel-card">
      <div className="admin-list-heading">
        <div>
          <span className="label">Users</span>
          <h2>{title}</h2>
        </div>
        <span>{items.length} مورد</span>
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>زمان ثبت‌نام</th>
              <th>شماره</th>
              <th>تلگرام</th>
              <th>اعتبار</th>
              <th>کد معرفی</th>
              <th>معرفی‌ها</th>
              <th>فعالیت</th>
              <th>کنترل اعتبار</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{formatDate(item.created_at)}</td>
                <td>{item.phone || "-"}</td>
                <td>{item.telegram_id || "-"}</td>
                <td>{item.credit_balance}</td>
                <td>{item.referral_code || "-"}</td>
                <td>{item.referral_count}</td>
                <td>{item.decodes_count} تحلیل · {item.paid_decodes_count} کامل · {item.contacts_count} مخاطب</td>
                <td>
                  <div className="admin-badges">
                    <button className="icon-button" onClick={() => item.phone && onAdjust(item.phone, 1)} disabled={!item.phone} aria-label="افزودن یک اعتبار"><PlusCircle size={16} /></button>
                    <button className="icon-button" onClick={() => item.phone && onAdjust(item.phone, -1)} disabled={!item.phone} aria-label="کم کردن یک اعتبار"><MinusCircle size={16} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function TelegramUserTable({ title, items, onAdjust }: { title: string; items: TelegramUsers["items"]; onAdjust: (phone: string, amount: number) => void }) {
  return (
    <div className="panel-card">
      <div className="admin-list-heading">
        <div>
          <span className="label">Telegram D1</span>
          <h2>{title}</h2>
        </div>
        <span>{items.length} مورد</span>
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>زمان ثبت‌نام</th>
              <th>شماره</th>
              <th>Telegram ID</th>
              <th>اعتبار</th>
              <th>کد معرفی</th>
              <th>معرفی‌ها</th>
              <th>معرف</th>
              <th>فعالیت</th>
              <th>کنترل اعتبار</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{formatDate(item.created_at)}</td>
                <td>{item.phone || "-"}</td>
                <td>{item.telegram_id}</td>
                <td>{item.credit_balance}</td>
                <td>{item.referral_code || "-"}</td>
                <td>{item.referral_count ?? 0}</td>
                <td>{item.referred_by_user_id || "-"}</td>
                <td>{item.decodes_count ?? 0} تحلیل · {item.paid_decodes_count ?? 0} کامل</td>
                <td>
                  <div className="admin-badges">
                    <button className="icon-button" onClick={() => item.phone && onAdjust(item.phone, 1)} disabled={!item.phone} aria-label="افزودن یک اعتبار"><PlusCircle size={16} /></button>
                    <button className="icon-button" onClick={() => item.phone && onAdjust(item.phone, -1)} disabled={!item.phone} aria-label="کم کردن یک اعتبار"><MinusCircle size={16} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function ActivityTable({ title, source, items }: { title: string; source: string; items: ActivityList["items"] | TelegramActivityList["items"] }) {
  return (
    <div className="panel-card">
      <div className="admin-list-heading">
        <div>
          <span className="label">{source}</span>
          <h2>{title}</h2>
        </div>
        <span>{items.length} مورد آخر</span>
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table admin-activity-table">
          <thead>
            <tr>
              <th>زمان</th>
              <th>رویداد</th>
              <th>شماره</th>
              <th>User ID</th>
              <th>جزئیات</th>
              <th>وضعیت</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={item.id}>
                <td>{formatDate(item.created_at)}</td>
                <td>
                  <div className="admin-event-title">
                    <strong>{item.title}</strong>
                    <span>{eventTypeLabel(item.event_type)}</span>
                  </div>
                </td>
                <td>{item.phone || "-"}</td>
                <td>{item.user_id || "-"}</td>
                <td>{item.detail || "-"}</td>
                <td>{item.status ? <span className={`admin-pill ${item.status}`}>{item.status}</span> : "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
  );
}

function BroadcastResultTable({ items }: { items: TelegramBroadcastResult[] }) {
  return (
    <div className="panel-card">
      <div className="admin-list-heading">
        <div>
          <span className="label">Broadcast report</span>
          <h2>گزارش ارسال ریلیس نوت</h2>
        </div>
        <span>{items.filter((item) => item.status === "sent").length} موفق · {items.filter((item) => item.status === "failed").length} ناموفق</span>
      </div>
      <div className="admin-table-wrap">
        <table className="admin-table">
          <thead>
            <tr>
              <th>شماره</th>
              <th>Telegram ID</th>
              <th>کد معرفی</th>
              <th>وضعیت</th>
              <th>خطا</th>
            </tr>
          </thead>
          <tbody>
            {items.map((item) => (
              <tr key={`${item.user_id}-${item.telegram_id}`}>
                <td>{item.phone || "-"}</td>
                <td>{item.telegram_id}</td>
                <td>{item.referral_code || "-"}</td>
                <td><span className={`admin-pill ${item.status}`}>{item.status === "sent" ? "ارسال شد" : "ناموفق"}</span></td>
                <td>{item.error || "-"}</td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    </div>
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

function eventTypeLabel(value: string) {
  return ({
    signup: "ثبت‌نام",
    free_decode: "تحلیل رایگان",
    paid_decode: "تحلیل کامل",
    payment: "پرداخت",
    contact: "مخاطب",
    copy: "کپی پاسخ",
    feedback: "بازخورد"
  } as Record<string, string>)[value] ?? value;
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
