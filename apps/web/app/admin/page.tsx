"use client";

import { useEffect, useRef, useState } from "react";
import { Beaker, BrainCircuit, ChevronLeft, ChevronRight, Download, FlaskConical, LockKeyhole, LogIn, LogOut, MinusCircle, PlusCircle, RefreshCw, Search, Send } from "lucide-react";
import {
  adminActivityList,
  adminLearningDaily,
  adminLogin,
  adminDecodeList,
  adminGrantAllCredits,
  adminGrantCredits,
  adminMetrics,
  adminRuleEngineCandidates,
  adminRuleEngineEval,
  adminRuleEngineExplain,
  adminUserList,
  LearningReport,
  RuleCandidateResponse,
  RuleEngineEval,
  RuleExplainResponse,
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

const USER_PAGE_SIZE = 50;
const ACTIVITY_PAGE_SIZE = 50;
const DECODE_PAGE_SIZE = 50;

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

  // صفحه‌بندی
  const [userOffset, setUserOffset] = useState(0);
  const [activityOffset, setActivityOffset] = useState(0);
  const [decodeOffset, setDecodeOffset] = useState(0);

  // یادگیری و موتور قانون
  const [learning, setLearning] = useState<LearningReport | null>(null);
  const [learningDate, setLearningDate] = useState("");
  const [learningLoading, setLearningLoading] = useState(false);
  const [ruleEval, setRuleEval] = useState<RuleEngineEval | null>(null);
  const [ruleEvalLoading, setRuleEvalLoading] = useState(false);
  const [candidates, setCandidates] = useState<RuleCandidateResponse | null>(null);
  const [candidatesLoading, setCandidatesLoading] = useState(false);
  const [explainMessage, setExplainMessage] = useState("");
  const [explainRelationship, setExplainRelationship] = useState("romantic");
  const [explainGoal, setExplainGoal] = useState("understand_only");
  const [explainResult, setExplainResult] = useState<RuleExplainResponse | null>(null);
  const [explainLoading, setExplainLoading] = useState(false);

  // رفرش خودکار
  const [autoRefresh, setAutoRefresh] = useState(false);
  const tokenRef = useRef("");
  tokenRef.current = token;

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
    setLearning(null);
    setRuleEval(null);
    setCandidates(null);
    setExplainResult(null);
    setAutoRefresh(false);
    setUserOffset(0);
    setActivityOffset(0);
    setDecodeOffset(0);
  }

  async function loadDashboard(offsets?: { user?: number; activity?: number; decode?: number }) {
    await loadDashboardWithToken(token, offsets);
  }

  async function loadDashboardWithToken(
    activeToken: string,
    offsets?: { user?: number; activity?: number; decode?: number }
  ) {
    const userOff = offsets?.user ?? userOffset;
    const activityOff = offsets?.activity ?? activityOffset;
    const decodeOff = offsets?.decode ?? decodeOffset;
    setError("");
    setLoading(true);
    try {
      const filters = {
        relationship_type: relationshipType,
        dominant_lens: dominantLens,
        safety_label: safetyLabel,
        prompt_version: promptVersion,
        limit: DECODE_PAGE_SIZE,
        offset: decodeOff
      };
      const results = await Promise.allSettled([
        adminMetrics(activeToken),
        adminDecodeList(activeToken, filters),
        adminUserList(activeToken, { q: userQuery, limit: USER_PAGE_SIZE, offset: userOff }),
        adminActivityList(activeToken, { q: userQuery, limit: ACTIVITY_PAGE_SIZE, offset: activityOff }),
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

  async function adjustCredits(target: { phone?: string | null; userId?: string | null }, amount: number) {
    const phone = target.phone || "";
    const userId = target.userId || "";
    const label = phone || `کاربر تلگرام ${userId}`;
    const verb = amount > 0 ? "اضافه" : "کم";
    if (!window.confirm(`برای ${label}، ${Math.abs(amount)} اعتبار ${verb} شود؟`)) return;
    setError("");
    setActionStatus("");
    try {
      if (phone) {
        await Promise.allSettled([
          adminGrantCredits(token, { phone, credits: amount }),
          telegramGrantCredits(token, { phone, credits: amount })
        ]);
        setActionStatus(`${amount} اعتبار برای شماره ${phone} اعمال شد، اگر در یکی از دیتابیس‌ها وجود داشته باشد.`);
      } else if (userId) {
        await telegramGrantCredits(token, { user_id: userId, credits: amount });
        setActionStatus(`${amount} اعتبار برای کاربر تلگرام اعمال شد.`);
      } else {
        return;
      }
      await loadDashboard();
    } catch (err) {
      setError(err instanceof Error ? err.message : "اعتبار اعمال نشد.");
    }
  }

  async function grantToPhone() {
    await adjustCredits({ phone: grantPhone }, grantAmount);
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

  // جستجوی تازه: offsetها صفر شوند
  function runSearch() {
    setUserOffset(0);
    setActivityOffset(0);
    setDecodeOffset(0);
    void loadDashboard({ user: 0, activity: 0, decode: 0 });
  }

  function pageUsers(delta: number) {
    const next = Math.max(0, userOffset + delta * USER_PAGE_SIZE);
    setUserOffset(next);
    void loadDashboard({ user: next });
  }

  function pageActivity(delta: number) {
    const next = Math.max(0, activityOffset + delta * ACTIVITY_PAGE_SIZE);
    setActivityOffset(next);
    void loadDashboard({ activity: next });
  }

  function pageDecodes(delta: number) {
    const next = Math.max(0, decodeOffset + delta * DECODE_PAGE_SIZE);
    setDecodeOffset(next);
    void loadDashboard({ decode: next });
  }

  async function loadLearning() {
    setError("");
    setLearningLoading(true);
    try {
      setLearning(await adminLearningDaily(token, learningDate));
    } catch (err) {
      setError(err instanceof Error ? err.message : "گزارش یادگیری دریافت نشد.");
    } finally {
      setLearningLoading(false);
    }
  }

  async function loadRuleEval() {
    setError("");
    setRuleEvalLoading(true);
    try {
      setRuleEval(await adminRuleEngineEval(token));
    } catch (err) {
      setError(err instanceof Error ? err.message : "ارزیابی موتور قانون انجام نشد.");
    } finally {
      setRuleEvalLoading(false);
    }
  }

  async function loadCandidates() {
    setError("");
    setCandidatesLoading(true);
    try {
      setCandidates(await adminRuleEngineCandidates(token, 50));
    } catch (err) {
      setError(err instanceof Error ? err.message : "کیس‌های کاندید دریافت نشد.");
    } finally {
      setCandidatesLoading(false);
    }
  }

  async function runExplain() {
    setError("");
    setExplainLoading(true);
    try {
      setExplainResult(
        await adminRuleEngineExplain(token, {
          message_text: explainMessage,
          relationship_type: explainRelationship,
          user_goal: explainGoal
        })
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "تست موتور قانون انجام نشد.");
    } finally {
      setExplainLoading(false);
    }
  }

  useEffect(() => {
    if (!autoRefresh || !token) return;
    const id = window.setInterval(() => {
      if (tokenRef.current) void loadDashboard();
    }, 30000);
    return () => window.clearInterval(id);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [autoRefresh, token]);

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
              <button className="primary admin-load-button" onClick={runSearch} disabled={loading}>
                {loading ? <RefreshCw className="animate-spin" size={16} /> : <Search size={16} />}
                <span>بارگذاری داشبورد</span>
              </button>
              <label className="field admin-autorefresh">
                <span className="label">رفرش خودکار (۳۰ث)</span>
                <input type="checkbox" checked={autoRefresh} onChange={(event) => setAutoRefresh(event.target.checked)} />
              </label>
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
              <Metric
                title="تکرار استفاده (میانگین اکشن/کاربر)"
                value={`${(metrics.frequency?.avg_actions_per_user ?? 0).toFixed(1)} (چنداکشنی: ${Math.round((metrics.frequency?.multi_action_rate ?? 0) * 100)}٪)`}
              />
              <Metric
                title="بررسی‌های قبل از ارسال"
                value={`${metrics.frequency?.before_send_checks ?? 0}`}
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
                <div className="admin-heading-actions">
                  <span>{decodes.total} مورد</span>
                  <CsvButton rows={decodes.items} filename="decodes" />
                </div>
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
              <Pager offset={decodeOffset} count={decodes.items.length} pageSize={DECODE_PAGE_SIZE} total={decodes.total} loading={loading} onPage={pageDecodes} />
            </div>
          ) : null}

          {users ? (
            <UserTable title="کاربران وب/API" items={users.items} onAdjust={adjustCredits} offset={userOffset} total={users.total} pageSize={USER_PAGE_SIZE} loading={loading} onPage={pageUsers} />
          ) : null}

          {telegramUsers ? (
            <TelegramUserTable title="کاربران تلگرام" items={telegramUsers.items} onAdjust={adjustCredits} />
          ) : null}

          {activities ? (
            <ActivityTable title="اتفاقات کاربران وب/API" source="Web/API" items={activities.items} offset={activityOffset} total={activities.total} pageSize={ACTIVITY_PAGE_SIZE} loading={loading} onPage={pageActivity} />
          ) : null}

          {telegramActivities ? (
            <ActivityTable title="اتفاقات کاربران تلگرام" source="Telegram D1" items={telegramActivities.items} />
          ) : null}

          <LearningPanel report={learning} loading={learningLoading} date={learningDate} setDate={setLearningDate} onLoad={loadLearning} disabled={!token} />

          <RuleEnginePanel
            evalResult={ruleEval}
            evalLoading={ruleEvalLoading}
            onLoadEval={loadRuleEval}
            candidates={candidates}
            candidatesLoading={candidatesLoading}
            onLoadCandidates={loadCandidates}
            explainResult={explainResult}
            explainLoading={explainLoading}
            explainMessage={explainMessage}
            setExplainMessage={setExplainMessage}
            explainRelationship={explainRelationship}
            setExplainRelationship={setExplainRelationship}
            explainGoal={explainGoal}
            setExplainGoal={setExplainGoal}
            onRunExplain={runExplain}
            disabled={!token}
          />
        </div>
      </section>
      )}
    </main>
  );
}

type AdjustTarget = { phone?: string | null; userId?: string | null };

function UserTable({ title, items, onAdjust, offset, total, pageSize, loading, onPage }: {
  title: string;
  items: UserList["items"];
  onAdjust: (target: AdjustTarget, amount: number) => void;
  offset: number;
  total: number;
  pageSize: number;
  loading: boolean;
  onPage: (delta: number) => void;
}) {
  return (
    <div className="panel-card">
      <div className="admin-list-heading">
        <div>
          <span className="label">Users</span>
          <h2>{title}</h2>
        </div>
        <div className="admin-heading-actions">
          <span>{total} مورد</span>
          <CsvButton rows={items} filename="web-users" />
        </div>
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
                    <button className="icon-button" onClick={() => item.phone && onAdjust({ phone: item.phone }, 1)} disabled={!item.phone} aria-label="افزودن یک اعتبار"><PlusCircle size={16} /></button>
                    <button className="icon-button" onClick={() => item.phone && onAdjust({ phone: item.phone }, -1)} disabled={!item.phone} aria-label="کم کردن یک اعتبار"><MinusCircle size={16} /></button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>
      <Pager offset={offset} count={items.length} pageSize={pageSize} total={total} loading={loading} onPage={onPage} />
    </div>
  );
}

function TelegramUserTable({ title, items, onAdjust }: { title: string; items: TelegramUsers["items"]; onAdjust: (target: AdjustTarget, amount: number) => void }) {
  return (
    <div className="panel-card">
      <div className="admin-list-heading">
        <div>
          <span className="label">Telegram D1</span>
          <h2>{title}</h2>
        </div>
        <div className="admin-heading-actions">
          <span>{items.length} مورد</span>
          <CsvButton rows={items} filename="telegram-users" />
        </div>
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
                    <button className="icon-button" onClick={() => onAdjust({ phone: item.phone, userId: item.id }, 1)} aria-label="افزودن یک اعتبار"><PlusCircle size={16} /></button>
                    <button className="icon-button" onClick={() => onAdjust({ phone: item.phone, userId: item.id }, -1)} aria-label="کم کردن یک اعتبار"><MinusCircle size={16} /></button>
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

function ActivityTable({ title, source, items, offset, total, pageSize, loading, onPage }: {
  title: string;
  source: string;
  items: ActivityList["items"] | TelegramActivityList["items"];
  offset?: number;
  total?: number;
  pageSize?: number;
  loading?: boolean;
  onPage?: (delta: number) => void;
}) {
  return (
    <div className="panel-card">
      <div className="admin-list-heading">
        <div>
          <span className="label">{source}</span>
          <h2>{title}</h2>
        </div>
        <div className="admin-heading-actions">
          <span>{total ?? items.length} مورد</span>
          <CsvButton rows={items} filename={`activity-${source.toLowerCase().replace(/[^a-z0-9]+/g, "-")}`} />
        </div>
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
      {onPage ? (
        <Pager offset={offset ?? 0} count={items.length} pageSize={pageSize ?? items.length} total={total ?? items.length} loading={loading ?? false} onPage={onPage} />
      ) : null}
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

function Pager({ offset, count, pageSize, total, loading, onPage }: {
  offset: number;
  count: number;
  pageSize: number;
  total: number;
  loading: boolean;
  onPage: (delta: number) => void;
}) {
  const from = total === 0 ? 0 : offset + 1;
  const to = offset + count;
  const hasPrev = offset > 0;
  const hasNext = to < total;
  if (!hasPrev && !hasNext) return null;
  return (
    <div className="admin-pager">
      <button className="secondary admin-load-button" onClick={() => onPage(-1)} disabled={!hasPrev || loading}>
        <ChevronRight size={16} />
        <span>قبلی</span>
      </button>
      <span className="admin-pager-info">{from}–{to} از {total}</span>
      <button className="secondary admin-load-button" onClick={() => onPage(1)} disabled={!hasNext || loading}>
        <span>بعدی</span>
        <ChevronLeft size={16} />
      </button>
    </div>
  );
}

function CsvButton({ rows, filename }: { rows: readonly object[]; filename: string }) {
  if (!rows.length) return null;
  return (
    <button className="secondary admin-load-button admin-csv-button" onClick={() => downloadCsv(rows as Record<string, unknown>[], filename)} aria-label="خروجی CSV">
      <Download size={16} />
      <span>CSV</span>
    </button>
  );
}

function LearningPanel({ report, loading, date, setDate, onLoad, disabled }: {
  report: LearningReport | null;
  loading: boolean;
  date: string;
  setDate: (value: string) => void;
  onLoad: () => void;
  disabled: boolean;
}) {
  const m = report?.metrics;
  return (
    <div className="panel-card">
      <div className="admin-list-heading">
        <div>
          <span className="label">Learning loop</span>
          <h2>گزارش یادگیری روزانه</h2>
        </div>
        <div className="admin-heading-actions">
          <input type="date" value={date} onChange={(event) => setDate(event.target.value)} aria-label="تاریخ گزارش" />
          <button className="primary admin-load-button" onClick={onLoad} disabled={disabled || loading}>
            {loading ? <RefreshCw className="animate-spin" size={16} /> : <BrainCircuit size={16} />}
            <span>دریافت گزارش</span>
          </button>
        </div>
      </div>
      {m ? (
        <>
          <p className="admin-panel-hint">پنجره: {m.report_date} (دیفالت: دیروز UTC)</p>
          <div className="result">
            <Metric title="کل تحلیل‌ها" value={m.total_decodes} />
            <Metric title="تحلیل کامل" value={m.paid_decodes} />
            <Metric title="نرخ کپی" value={`${Math.round(m.copy_rate * 100)}٪`} />
            <Metric title="فیدبک" value={m.feedback_count} />
            <Metric title="فیدبک مثبت" value={`${Math.round(m.positive_feedback_rate * 100)}٪`} />
            <Metric title="فیدبک منفی" value={`${Math.round(m.negative_feedback_rate * 100)}٪`} />
            <Metric title="میانگین پشیمانی" value={m.average_regret_score ?? "—"} />
            <Metric title="ترکیب لنز" value={m.lens_mix.map((x) => `${x.dominant_lens}: ${x.count}`).join("، ") || "—"} />
            <Metric title="ترکیب ایمنی" value={m.safety_mix.map((x) => `${x.safety_label}: ${x.count}`).join("، ") || "—"} />
          </div>
          {report?.recommendations?.length ? (
            <ul className="admin-reco-list">
              {report.recommendations.map((rec, index) => (
                <li key={index}>{rec}</li>
              ))}
            </ul>
          ) : null}
        </>
      ) : (
        <p className="admin-panel-hint">برای دیدن متریک‌های روزانه و توصیه‌های خودکار، یک تاریخ انتخاب کنید (یا خالی بگذارید برای دیروز) و «دریافت گزارش» را بزنید.</p>
      )}
    </div>
  );
}

function RuleEnginePanel(props: {
  evalResult: RuleEngineEval | null;
  evalLoading: boolean;
  onLoadEval: () => void;
  candidates: RuleCandidateResponse | null;
  candidatesLoading: boolean;
  onLoadCandidates: () => void;
  explainResult: RuleExplainResponse | null;
  explainLoading: boolean;
  explainMessage: string;
  setExplainMessage: (value: string) => void;
  explainRelationship: string;
  setExplainRelationship: (value: string) => void;
  explainGoal: string;
  setExplainGoal: (value: string) => void;
  onRunExplain: () => void;
  disabled: boolean;
}) {
  const ev = props.evalResult;
  return (
    <div className="panel-card">
      <div className="admin-list-heading">
        <div>
          <span className="label">Rule engine</span>
          <h2>کیفیت و تست موتور قانون</h2>
        </div>
        <div className="admin-heading-actions">
          <button className="primary admin-load-button" onClick={props.onLoadEval} disabled={props.disabled || props.evalLoading}>
            {props.evalLoading ? <RefreshCw className="animate-spin" size={16} /> : <FlaskConical size={16} />}
            <span>ارزیابی</span>
          </button>
          <button className="secondary admin-load-button" onClick={props.onLoadCandidates} disabled={props.disabled || props.candidatesLoading}>
            {props.candidatesLoading ? <RefreshCw className="animate-spin" size={16} /> : <Beaker size={16} />}
            <span>کیس‌های کاندید</span>
          </button>
        </div>
      </div>

      {ev ? (
        <>
          <p className="admin-panel-hint">نسخه موتور: {ev.rule_engine_version} · {ev.metrics.case_count} کیس تست</p>
          <div className="result">
            <Metric title="دقت لنز" value={`${Math.round(ev.metrics.lens_accuracy * 100)}٪`} />
            <Metric title="دقت ایمنی" value={`${Math.round(ev.metrics.safety_accuracy * 100)}٪`} />
            <Metric title="بازیابی لحن" value={`${Math.round(ev.metrics.tone_recall * 100)}٪`} />
            <Metric title="خطاها" value={ev.misses.length} />
          </div>
          {Object.keys(ev.metrics.lens_confusion).length ? (
            <p className="admin-panel-hint">خطای لنز: {Object.entries(ev.metrics.lens_confusion).map(([k, v]) => `${k} (${v})`).join("، ")}</p>
          ) : null}
          {ev.recommendations?.length ? (
            <ul className="admin-reco-list">
              {ev.recommendations.map((rec, index) => (
                <li key={index}>{rec}</li>
              ))}
            </ul>
          ) : null}
          {ev.misses.length ? (
            <div className="admin-table-wrap">
              <table className="admin-table">
                <thead>
                  <tr>
                    <th>کیس</th>
                    <th>لنز (انتظار/واقعی)</th>
                    <th>ایمنی (انتظار/واقعی)</th>
                    <th>لحن‌های جاافتاده</th>
                  </tr>
                </thead>
                <tbody>
                  {ev.misses.map((row) => (
                    <tr key={row.id}>
                      <td>{row.id}</td>
                      <td><span className={row.lens_ok ? "" : "admin-pill high_risk"}>{row.expected_lens} → {row.actual_lens}</span></td>
                      <td><span className={row.safety_ok ? "" : "admin-pill watch"}>{row.expected_safety_label} → {row.actual_safety_label}</span></td>
                      <td>{row.missing_tones.join("، ") || "—"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          ) : null}
        </>
      ) : null}

      {props.candidates ? (
        <div className="admin-subsection">
          <div className="admin-list-heading">
            <div>
              <span className="label">Candidate cases</span>
              <h3>نمونه‌های فیدبک منفی برای eval set</h3>
            </div>
            <div className="admin-heading-actions">
              <span>{props.candidates.candidate_count} مورد</span>
              <CsvButton rows={props.candidates.candidate_cases.map(flattenCandidate)} filename="rule-candidates" />
            </div>
          </div>
          <p className="admin-panel-hint">{props.candidates.selection_rule}</p>
          <div className="admin-table-wrap">
            <table className="admin-table">
              <thead>
                <tr>
                  <th>زمان</th>
                  <th>پیام</th>
                  <th>رابطه/هدف</th>
                  <th>طبقه‌بندی فعلی</th>
                  <th>سیگنال فیدبک</th>
                </tr>
              </thead>
              <tbody>
                {props.candidates.candidate_cases.map((c) => (
                  <tr key={c.feedback_id}>
                    <td>{formatDate(c.created_at)}</td>
                    <td>{c.message_preview || "—"}</td>
                    <td>{relationshipLabel(c.relationship_type)} · {c.user_goal}</td>
                    <td>{lensLabel(c.current_classification.dominant_lens)} · <span className={`admin-pill ${c.current_classification.safety_label}`}>{c.current_classification.safety_label}</span></td>
                    <td>{[c.feedback_signals.user_rating, c.feedback_signals.outcome, c.feedback_signals.regret_score != null ? `regret ${c.feedback_signals.regret_score}` : null, c.feedback_signals.user_comment].filter(Boolean).join(" · ") || "—"}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      ) : null}

      <div className="admin-subsection">
        <div className="admin-list-heading">
          <div>
            <span className="label">Explain</span>
            <h3>تست زندهٔ طبقه‌بندی یک پیام</h3>
          </div>
        </div>
        <label className="field">
          <span className="label">متن پیام</span>
          <textarea value={props.explainMessage} onChange={(event) => props.setExplainMessage(event.target.value)} rows={3} placeholder="پیام را بنویس تا لنز، ایمنی و لحن‌ها را ببینی" />
        </label>
        <div className="admin-toolbar">
          <label className="field">
            <span className="label">نوع رابطه</span>
            <select value={props.explainRelationship} onChange={(event) => props.setExplainRelationship(event.target.value)}>
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
            <span className="label">هدف</span>
            <select value={props.explainGoal} onChange={(event) => props.setExplainGoal(event.target.value)}>
              <option value="understand_only">فقط درک</option>
              <option value="calm_conflict">آرام‌کردن تنش</option>
              <option value="set_boundary">مرزگذاری</option>
              <option value="improve_relationship">بهبود رابطه</option>
              <option value="professional_reply">پاسخ حرفه‌ای</option>
              <option value="make_them_accountable">پاسخ‌گو کردن</option>
              <option value="avoid_needy">نیازمند به‌نظر نرسیدن</option>
              <option value="end_conversation">پایان گفتگو</option>
            </select>
          </label>
          <button className="primary admin-load-button" onClick={props.onRunExplain} disabled={props.disabled || props.explainLoading || !props.explainMessage.trim()}>
            {props.explainLoading ? <RefreshCw className="animate-spin" size={16} /> : <Search size={16} />}
            <span>تحلیل کن</span>
          </button>
        </div>
        {props.explainResult ? (
          <pre className="admin-json">{JSON.stringify(props.explainResult, null, 2)}</pre>
        ) : null}
      </div>
    </div>
  );
}

function flattenCandidate(c: RuleCandidateResponse["candidate_cases"][number]) {
  return {
    feedback_id: c.feedback_id,
    decode_id: c.decode_id,
    created_at: c.created_at,
    message_preview: c.message_preview,
    relationship_type: c.relationship_type,
    user_goal: c.user_goal,
    dominant_lens: c.current_classification.dominant_lens,
    safety_label: c.current_classification.safety_label,
    user_rating: c.feedback_signals.user_rating,
    outcome: c.feedback_signals.outcome,
    regret_score: c.feedback_signals.regret_score,
    user_comment: c.feedback_signals.user_comment
  };
}

function downloadCsv(rows: Record<string, unknown>[], filename: string) {
  if (!rows.length) return;
  const headers = Array.from(rows.reduce((set, row) => {
    Object.keys(row).forEach((key) => set.add(key));
    return set;
  }, new Set<string>()));
  const escape = (value: unknown) => {
    if (value === null || value === undefined) return "";
    const text = typeof value === "object" ? JSON.stringify(value) : String(value);
    return /[",\n]/.test(text) ? `"${text.replace(/"/g, '""')}"` : text;
  };
  const lines = [headers.join(","), ...rows.map((row) => headers.map((key) => escape(row[key])).join(","))];
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8;" });
  const url = URL.createObjectURL(blob);
  const link = document.createElement("a");
  link.href = url;
  link.download = `${filename}-${new Date().toISOString().slice(0, 10)}.csv`;
  document.body.appendChild(link);
  link.click();
  document.body.removeChild(link);
  URL.revokeObjectURL(url);
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
