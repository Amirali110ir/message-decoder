"use client";

import {
  Activity,
  AlertCircle,
  Award,
  BookOpenCheck,
  BrainCircuit,
  Check,
  Compass,
  Copy,
  CreditCard,
  EyeOff,
  Fingerprint,
  Flame,
  Glasses,
  History,
  HeartHandshake,
  LockKeyhole,
  LogIn,
  MessageCircle,
  MessageSquareCode,
  MessageSquareText,
  Radar,
  RefreshCw,
  Scale,
  Save,
  ShieldCheck,
  ShieldAlert,
  Sparkles,
  Target,
  Trash2,
  User,
  UserPlus,
  Users,
  Zap
} from "lucide-react";
import Link from "next/link";
import { useEffect, useState } from "react";
import type { Contact, DecodeHistoryItem, RelationshipThermometer } from "../../lib/api";
import {
  copyEvent,
  createContact,
  createPayment,
  deleteContact,
  deleteDecode,
  deleteStoredData,
  freeDecode,
  FreeDecodeResponse,
  getContacts,
  getCredits,
  getDecodeHistory,
  getReferral,
  getRelationshipThermometer,
  paidDecode,
  paidDecodeGhost,
  PaidDecodeResponse,
  notifyTelegramOtp,
  requestOtp,
  sendFeedback,
  sendSelectedReplyFeedback,
  updateContact,
  verifyPayment,
  verifyOtpWithReferral
} from "../../lib/api";

const relationshipOptions = [
  ["romantic", "رابطه عاطفی"],
  ["ex", "رابطه تمام‌شده / اکس"],
  ["friend", "دوست یا آشنا"],
  ["family", "خانواده"],
  ["manager_colleague", "مدیر یا همکار"],
  ["customer", "مشتری یا خریدار"],
  ["unknown", "نامشخص"]
] as const;

const goalOptions = [
  ["calm_conflict", "تنش را کمتر کنم"],
  ["set_boundary", "محکم اما محترمانه مرز بگذارم"],
  ["improve_relationship", "رابطه را ترمیم کنم"],
  ["professional_reply", "پاسخ حرفه‌ای و کوتاه بدهم"],
  ["make_them_accountable", "مسئولیت را شفاف کنم"],
  ["avoid_needy", "نیازمند یا دفاعی دیده نشوم"],
  ["end_conversation", "مکالمه را محترمانه ببندم"],
  ["understand_only", "فعلاً فقط پیام را بفهمم"]
] as const;

const playbookTemplates = [
  {
    title: "پیام سرد عاطفی",
    relationship: "romantic",
    goal: "avoid_needy",
    message: "باشه، هر جور راحتی. معلومه که اصلاً برات مهم نیست.",
    context: "طرف مقابل بعد از تأخیر در جواب دادن این پیام را فرستاده است."
  },
  {
    title: "پیگیری کاری",
    relationship: "manager_colleague",
    goal: "professional_reply",
    message: "این گزارش قرار بود دیروز آماده باشد. چرا هنوز باید پیگیری کنم؟",
    context: "می‌خواهم مسئولیت‌پذیر باشم اما بیش از حد دفاعی یا عذرخواه دیده نشوم."
  },
  {
    title: "مرزبندی با اکس",
    relationship: "ex",
    goal: "end_conversation",
    message: "پس یعنی همه چیز برای تو انقدر راحت تموم شد؟",
    context: "نمی‌خواهم مکالمه دوباره وارد بحث فرسایشی گذشته شود."
  },
  {
    title: "دلخوری دوست",
    relationship: "friend",
    goal: "calm_conflict",
    message: "دیگه لازم نیست توضیح بدی، فهمیدم اولویتت کیه.",
    context: "می‌خواهم تنش کمتر شود و سوءتفاهم را مستقیم‌تر روشن کنم."
  }
] as const;

export default function DecoderPage() {
  const [message, setMessage] = useState("");
  const [relationship, setRelationship] = useState("romantic");
  const [goal, setGoal] = useState("avoid_needy");
  const [context, setContext] = useState("");
  const [consent, setConsent] = useState<"none" | "history" | "anonymized">("none");
  const [ghostMode, setGhostMode] = useState(false);
  const [freeResult, setFreeResult] = useState<FreeDecodeResponse | null>(null);
  const [freeResultGhost, setFreeResultGhost] = useState(false);
  const [paidResult, setPaidResult] = useState<PaidDecodeResponse | null>(null);
  const [showAdvancedInputs, setShowAdvancedInputs] = useState(false);
  const [contacts, setContacts] = useState<Contact[]>([]);
  const [historyItems, setHistoryItems] = useState<DecodeHistoryItem[]>([]);
  const [selectedContactId, setSelectedContactId] = useState("");
  const [relationshipThermometer, setRelationshipThermometer] = useState<RelationshipThermometer | null>(null);
  const [contactName, setContactName] = useState("");
  const [contactProfile, setContactProfile] = useState("");
  const [contactsLoading, setContactsLoading] = useState(false);
  const [historyLoading, setHistoryLoading] = useState(false);
  const [phone, setPhone] = useState("");
  const [otp, setOtp] = useState("");
  const [otpSent, setOtpSent] = useState(false);
  const [referralCode, setReferralCode] = useState("");
  const [myReferral, setMyReferral] = useState<{ referral_code: string; referral_url: string; reward_credits: number } | null>(null);
  const [token, setToken] = useState("");
  const [credits, setCredits] = useState(0);
  const [loading, setLoading] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);

  useEffect(() => {
    const savedToken = window.localStorage.getItem("message-decoder-token") || "";
    const savedPhone = window.localStorage.getItem("message-decoder-phone") || "";
    if (!savedToken) return;
    setToken(savedToken);
    setPhone(savedPhone);
    void hydrateAccount(savedToken);
  }, []);

  async function hydrateAccount(authToken: string) {
    try {
      const [creditResult, referralResult] = await Promise.all([
        getCredits(authToken),
        getReferral(authToken)
      ]);
      setCredits(creditResult.credit_balance);
      setMyReferral(referralResult);
      await Promise.all([refreshContacts(authToken), refreshHistory(authToken)]);
    } catch (err) {
      window.localStorage.removeItem("message-decoder-token");
      setToken("");
    }
  }

  async function handleFreeDecode() {
    if (!message.trim()) return;
    setError("");
    setLoading(true);
    setStatus("داریم پیام را از نظر لحن، ریسک و نیاز احتمالی می‌خوانیم...");
    setPaidResult(null);
    try {
      const result = await freeDecode({
        message_text: message,
        relationship_type: relationship as never,
        user_goal: goal as never,
        optional_context: context || undefined,
        privacy_consent: ghostMode ? "none" : consent,
        contact_id: selectedContactId || undefined,
        contact_name: !selectedContactId && contactName.trim() ? contactName.trim() : undefined,
        ghost_mode: ghostMode
      }, token || undefined);
      setFreeResult(result);
      setFreeResultGhost(ghostMode);
      if (result.contact_id) {
        setSelectedContactId(result.contact_id);
      }
      if (token && selectedContactId && !ghostMode) {
        await refreshContacts(token);
        await refreshRelationshipThermometer(selectedContactId, token);
      } else if (token && result.contact_id && !ghostMode) {
        await refreshContacts(token);
        await refreshRelationshipThermometer(result.contact_id, token);
      }
      if (token && consent === "history" && !ghostMode) {
        await refreshHistory(token);
      }
      setStatus(ghostMode ? "تحلیل آماده است و در حالت شبح ذخیره نشد." : "تحلیل آماده است؛ قبل از جواب دادن، برداشت محتمل و ریسک مکالمه را ببینید.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "تحلیل پیام انجام نشد. چند لحظه دیگر دوباره تلاش کنید.");
      setStatus("");
    } finally {
      setLoading(false);
    }
  }

  async function handleOtp() {
    if (!phone.trim()) {
      setError("برای ساخت پاسخ‌های کامل، شماره موبایل را وارد کنید. اگر همین شماره در تلگرام وصل باشد، کد ورود را آنجا هم می‌گیرید.");
      return;
    }
    setError("");
    setStatus("داریم کد ورود را می‌فرستیم...");
    try {
      const result = await requestOtp(phone);
      await notifyTelegramOtp(result.telegram_payload);
      setOtpSent(true);
      setStatus("کد ورود ارسال شد. اگر همین شماره در تلگرام وصل باشد، کد داخل تلگرام هم ارسال می‌شود.");
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
      const result = await verifyOtpWithReferral(phone, otp, referralCode || undefined);
      setToken(result.token);
      setCredits(result.credit_balance);
      window.localStorage.setItem("message-decoder-token", result.token);
      window.localStorage.setItem("message-decoder-phone", phone);
      await Promise.all([refreshContacts(result.token), refreshHistory(result.token)]);
      setMyReferral(await getReferral(result.token));
      setStatus("حساب فعال شد؛ حالا می‌توانید پاسخ کامل و قابل کپی بسازید.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "این کد درست نیست یا منقضی شده است.");
      setStatus("");
    }
  }

  async function handleBuyCredits() {
    if (!token) {
      setError("اول شماره موبایل را تایید کنید تا اعتبار به حساب شما اضافه شود.");
      return;
    }
    setError("");
    setStatus("داریم اعتبار را فعال می‌کنیم...");
    try {
      const payment = await createPayment(token, "credits_5");
      window.localStorage.setItem("message-decoder-token", token);
      window.localStorage.setItem("message-decoder-pending-payment", payment.payment_id);
      if (!payment.payment_url.includes("sandbox.zarinpal.com")) {
        window.location.assign(payment.payment_url);
        return;
      }
      const verified = await verifyPayment(token, payment.payment_id);
      window.localStorage.removeItem("message-decoder-pending-payment");
      setCredits(verified.credit_balance);
      setStatus("۵ اعتبار اضافه شد؛ می‌توانید چند پاسخ کامل دیگر هم بسازید.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "اعتبار فعال نشد. دوباره تلاش کنید.");
      setStatus("");
    }
  }

  async function handlePaidDecode() {
    if (!freeResult?.free_output) return;
    if (freeResultGhost && !token) {
      setError("برای ساخت پاسخ‌های کامل در حالت شبح هم اول شماره موبایل را تایید کنید. متن پیام ذخیره نمی‌شود.");
      return;
    }
    if (!token) {
      setError("برای ساخت پاسخ‌های کامل و قابل کپی، اول شماره موبایل را تایید کنید.");
      return;
    }
    setError("");
    setLoading(true);
    setStatus("داریم پاسخ‌هایی می‌سازیم که هم روشن باشند، هم تنش را بی‌دلیل بالا نبرند...");
    try {
      const result = freeResultGhost
        ? await paidDecodeGhost(token, {
            decode_id: freeResult.decode_id,
            free_output: freeResult.free_output,
            message_text: message,
            relationship_type: relationship as never,
            user_goal: goal as never,
            optional_context: context.trim() || undefined
          })
        : await paidDecode(token, freeResult.decode_id);
      setPaidResult(result);
      setCredits(result.credit_balance);
      setStatus(freeResultGhost
        ? "پاسخ‌ها آماده‌اند و تحلیل شبح در تاریخچه ذخیره نشد."
        : "پاسخ‌ها آماده‌اند؛ یکی را انتخاب کنید، اگر لازم بود ویرایش کنید و بعد بفرستید."
      );
    } catch (err) {
      setError(err instanceof Error ? err.message : "پاسخ کامل ساخته نشد. دوباره تلاش کنید.");
      setStatus("");
    } finally {
      setLoading(false);
    }
  }

  async function handleCopy(text: string, label: string) {
    try {
      await navigator.clipboard.writeText(text);
      setCopiedIndex(label);
      if (freeResult && !freeResultGhost) {
        await copyEvent(freeResult.decode_id, label, label);
      }
      setTimeout(() => setCopiedIndex(null), 2000);
    } catch (err) {
      setError("کپی خودکار انجام نشد. می‌توانید متن پاسخ را دستی انتخاب و کپی کنید.");
    }
  }

  async function handleFeedback(user_rating: string, outcome?: string, regret_score?: number) {
    if (!freeResult) return;
    if (freeResultGhost) {
      setStatus("این تحلیل در حالت شبح ذخیره نشده؛ بازخورد هم برای حفظ حریم خصوصی ارسال نشد.");
      return;
    }
    try {
      await sendFeedback({
        decode_id: freeResult.decode_id,
        user_rating,
        outcome,
        regret_score,
        copied_response: Boolean(paidResult)
      });
      setStatus("بازخورد ثبت شد؛ همین داده‌ها کمک می‌کند پاسخ‌های بعدی دقیق‌تر شوند.");
    } catch (err) {
      // Feedback should never interrupt the main flow.
    }
  }

  async function handleSelectedReply(label: string, outcome?: string) {
    if (!freeResult || freeResultGhost) return;
    try {
      await sendSelectedReplyFeedback({
        decode_id: freeResult.decode_id,
        selected_reply_label: label,
        copied_response: copiedIndex === label,
        outcome,
        contact_id: selectedContactId || undefined
      }, token || undefined);
      if (token && selectedContactId) {
        await refreshContacts(token);
      }
      setStatus(outcome ? "انتخاب پاسخ و نتیجه ثبت شد." : "انتخاب پاسخ ثبت شد؛ از همین برای دقیق‌تر شدن پیشنهادهای بعدی استفاده می‌کنیم.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "انتخاب پاسخ ثبت نشد.");
    }
  }

  async function refreshContacts(authToken = token) {
    if (!authToken) return;
    setContactsLoading(true);
    try {
      setContacts(await getContacts(authToken));
    } catch (err) {
      setError(err instanceof Error ? err.message : "فهرست مخاطبین دریافت نشد.");
    } finally {
      setContactsLoading(false);
    }
  }

  async function refreshHistory(authToken = token) {
    if (!authToken) return;
    setHistoryLoading(true);
    try {
      const result = await getDecodeHistory(authToken);
      setHistoryItems(result.items);
    } catch (err) {
      setError(err instanceof Error ? err.message : "تاریخچه دریافت نشد.");
    } finally {
      setHistoryLoading(false);
    }
  }

  function handleSelectContact(contactId: string) {
    setSelectedContactId(contactId);
    const contact = contacts.find((item) => item.id === contactId);
    if (contact) {
      setContactName(contact.name);
      setContactProfile(contact.profile_summary ?? "");
      setRelationship(contact.relationship_type);
      if (contact.default_goal) {
        setGoal(contact.default_goal);
      }
      if (token) {
        refreshRelationshipThermometer(contact.id, token);
      }
    } else {
      setContactName("");
      setContactProfile("");
      setRelationshipThermometer(null);
    }
  }

  async function refreshRelationshipThermometer(contactId = selectedContactId, authToken = token) {
    if (!authToken || !contactId) return;
    try {
      setRelationshipThermometer(await getRelationshipThermometer(authToken, contactId));
    } catch (err) {
      setRelationshipThermometer(null);
    }
  }

  async function handleSaveContact() {
    if (!token) {
      setError("برای ساخت پرونده مخاطب، اول شماره موبایل را تایید کنید.");
      return;
    }
    if (!contactName.trim()) {
      setError("نام مخاطب را وارد کنید.");
      return;
    }
    setError("");
    setContactsLoading(true);
    try {
      const payload = {
        name: contactName.trim(),
        relationship_type: relationship as never,
        default_goal: goal as never,
        profile_summary: contactProfile.trim() || null
      };
      const contact = selectedContactId
        ? await updateContact(token, selectedContactId, payload)
        : await createContact(token, payload);
      setContacts((items) => selectedContactId
        ? items.map((item) => (item.id === selectedContactId ? contact : item))
        : [contact, ...items]
      );
      setSelectedContactId(contact.id);
      setContactName(contact.name);
      setContactProfile(contact.profile_summary ?? "");
      await refreshRelationshipThermometer(contact.id, token);
      setStatus(selectedContactId ? "پرونده مخاطب به‌روزرسانی شد." : "پرونده مخاطب ساخته شد و به تحلیل بعدی وصل می‌شود.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "پرونده مخاطب ذخیره نشد.");
    } finally {
      setContactsLoading(false);
    }
  }

  async function handleDeleteContact() {
    if (!token || !selectedContactId) return;
    setError("");
    setContactsLoading(true);
    try {
      await deleteContact(token, selectedContactId);
      setContacts((items) => items.filter((item) => item.id !== selectedContactId));
      setSelectedContactId("");
      setContactName("");
      setContactProfile("");
      setRelationshipThermometer(null);
      setStatus("پرونده مخاطب حذف شد.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "پرونده مخاطب حذف نشد.");
    } finally {
      setContactsLoading(false);
    }
  }

  async function handleDeleteHistoryItem(decodeId: string) {
    if (!token) return;
    setError("");
    setHistoryLoading(true);
    try {
      await deleteDecode(token, decodeId);
      setHistoryItems((items) => items.filter((item) => item.id !== decodeId));
      if (freeResult?.decode_id === decodeId) {
        setFreeResult(null);
        setPaidResult(null);
      }
      setStatus("این تحلیل از تاریخچه و داده‌های ذخیره‌شده حذف شد.");
    } catch (err) {
      setError(err instanceof Error ? err.message : "حذف تحلیل انجام نشد.");
    } finally {
      setHistoryLoading(false);
    }
  }

  async function handleDeleteStoredData() {
    if (!token) return;
    setError("");
    setHistoryLoading(true);
    try {
      const result = await deleteStoredData(token);
      setHistoryItems([]);
      setContacts([]);
      setSelectedContactId("");
      setRelationshipThermometer(null);
      setContactName("");
      setContactProfile("");
      setFreeResult(null);
      setPaidResult(null);
      setStatus(`${result.deleted_decodes} تحلیل و ${result.deleted_contacts} مخاطب از داده‌های ذخیره‌شده حذف شد.`);
    } catch (err) {
      setError(err instanceof Error ? err.message : "حذف داده‌های ذخیره‌شده انجام نشد.");
    } finally {
      setHistoryLoading(false);
    }
  }

  function applyPlaybookTemplate(template: (typeof playbookTemplates)[number]) {
    setMessage(template.message);
    setRelationship(template.relationship);
    setGoal(template.goal);
    setContext(template.context);
    setFreeResult(null);
    setPaidResult(null);
    setStatus(`سناریوی «${template.title}» آماده شد.`);
  }

  const selectedContact = contacts.find((item) => item.id === selectedContactId);

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
              <span className="brand-subtitle">تحلیل پیام قبل از پاسخ</span>
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
                <span>وب و تلگرام فعال</span>
              </div>
            )}
            <Link className="nav-login" href="/">
              صفحه اصلی
            </Link>
          </div>
        </div>
      </header>

      <section className="decoder-section decoder-app-section" id="decoder">
        <div className="shell">
          <div className="section-heading">
            <span>تحلیل اول بدون ورود</span>
            <h1>پیام را اینجا بگذارید؛ قبل از جواب دادن ریسک را ببینید</h1>
            <p>پیام را وارد کنید تا برداشت محتمل، ریسک جواب عجولانه و مسیر پاسخ کم‌تنش‌تر را ببینید. تنظیمات بیشتر بعد از تحلیل در دسترس‌اند.</p>
          </div>

          <div className="workspace-grid">
            <div className="panel-card form-grid">
              <div className="panel-title">
                <MessageSquareCode size={19} />
                <div>
                  <h3>متن پیام</h3>
                  <p>پیام را همان‌طور که دریافت کرده‌اید وارد کنید. برای حفظ حریم خصوصی، نام، شماره، آدرس و جزئیات حساس را حذف کنید.</p>
                </div>
              </div>

              <div className="playbook-strip">
                <div className="field-label">
                  <BookOpenCheck size={16} />
                  <span>نمونه پیام‌های آماده</span>
                </div>
                <div className="playbook-actions">
                  {playbookTemplates.map((template) => (
                    <button className="mini-action" type="button" key={template.title} onClick={() => applyPlaybookTemplate(template)}>
                      {template.title}
                    </button>
                  ))}
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

              <button
                className="mini-action advanced-toggle"
                type="button"
                onClick={() => setShowAdvancedInputs((value) => !value)}
              >
                {showAdvancedInputs ? "بستن گزینه‌های بیشتر" : "زمینه یا حریم خصوصی را تنظیم کنم"}
              </button>

              {showAdvancedInputs && (
                <div className="advanced-inputs">
                  <div className="field-group">
                    <label className="field-label">
                      <Fingerprint size={16} />
                      <span>زمینه کوتاه، اگر کمک می‌کند</span>
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
                      <option value="none">پیام را ذخیره نکن.</option>
                      <option value="history">در تاریخچه حساب من نگه دار.</option>
                      <option value="anonymized">بدون نام برای بهتر شدن تحلیل‌ها استفاده کن.</option>
                    </select>
                  </div>

                  <label className={`ghost-toggle ${ghostMode ? "active" : ""}`}>
                    <input
                      type="checkbox"
                      checked={ghostMode}
                      onChange={(event) => setGhostMode(event.target.checked)}
                    />
                    <span className="ghost-toggle-icon">
                      <ShieldCheck size={18} />
                    </span>
                    <span>
                      <strong>حالت شبح</strong>
                      <small>تحلیل و پاسخ کامل در تاریخچه ذخیره نمی‌شود. فقط برای ساخت پاسخ، همین صفحه از متن استفاده می‌کند.</small>
                    </span>
                  </label>
                </div>
              )}

              {token && freeResult && (
              <div className="contact-memory-card">
                <div className="contact-memory-header">
                  <div className="field-label">
                    <UserPlus size={16} />
                    <span>پرونده مخاطب</span>
                  </div>
                  {token && (
                    <button className="mini-action" type="button" onClick={() => refreshContacts()} disabled={contactsLoading}>
                      <RefreshCw className={contactsLoading ? "animate-spin" : ""} size={14} />
                      <span>به‌روزرسانی</span>
                    </button>
                  )}
                </div>
                {!token ? (
                  <div className="contact-empty-note">
                    بعد از ورود، می‌توانید یک مخاطب انتخاب کنید تا زمینه رفتاری او در تحلیل همین پیام لحاظ شود.
                  </div>
                ) : (
                  <>
                    {contacts.length === 0 && !contactsLoading && (
                    <div className="contact-empty-note">
                        هنوز مخاطبی ندارید. یک نام کوتاه ثبت کنید تا تحلیل‌های بعدی همین رابطه دقیق‌تر شوند و دماسنج رابطه روند گرمی، تنش و دفاعی‌تر شدن گفتگو را از روی تحلیل‌های ذخیره‌شده همین مخاطب نشان دهد.
                      </div>
                    )}
                    <select value={selectedContactId} onChange={(event) => handleSelectContact(event.target.value)}>
                      <option value="">بدون مخاطب ذخیره‌شده</option>
                      {contacts.map((contact) => (
                        <option value={contact.id} key={contact.id}>
                          {contact.name} · {contact.interaction_count} تحلیل
                        </option>
                      ))}
                    </select>
                    {selectedContactId && (
                      <div className="selected-contact-note">
                        <strong>{selectedContact?.name}</strong>
                        <span>{selectedContact?.memory_summary || selectedContact?.profile_summary || "برای این مخاطب هنوز خلاصه رفتاری ثبت نشده است."}</span>
                      </div>
                    )}
                    {selectedContactId && relationshipThermometer && (
                      <div className="relationship-thermometer">
                        <div>
                          <strong>{relationshipThermometer.label}</strong>
                          <span>{relationshipThermometer.summary}</span>
                        </div>
                        <div className="thermometer-bars">
                          <span>گرمی رابطه</span>
                          <div className="mini-meter"><i style={{ width: `${relationshipThermometer.warmth_score}%` }} /></div>
                          <span>روند تدافعی {relationshipThermometer.defensive_trend > 0 ? "+" : ""}{relationshipThermometer.defensive_trend}</span>
                        </div>
                      </div>
                    )}
                    <div className="contact-create-grid">
                      <input
                        value={contactName}
                        onChange={(event) => setContactName(event.target.value)}
                        placeholder="نام مخاطب"
                      />
                      <button className="btn-secondary btn-compact" type="button" onClick={handleSaveContact} disabled={contactsLoading}>
                        <Save size={15} />
                        <span>{selectedContactId ? "ویرایش" : "ذخیره"}</span>
                      </button>
                    </div>
                    <textarea
                      className="compact-textarea"
                      value={contactProfile}
                      onChange={(event) => setContactProfile(event.target.value)}
                      placeholder="خلاصه رفتاری اختیاری، مثلاً: به سکوت حساس است و با توضیح مستقیم آرام‌تر می‌شود."
                    />
                    {selectedContactId && (
                      <div className="contact-secondary-actions">
                        <button className="mini-action" type="button" onClick={() => handleSelectContact("")}>
                          مخاطب جدید
                        </button>
                        <button className="mini-action danger-action" type="button" onClick={handleDeleteContact} disabled={contactsLoading}>
                          حذف مخاطب
                        </button>
                      </div>
                    )}
                  </>
                )}
              </div>
              )}

              {token && freeResult && (
                <div className="history-memory-card">
                  <div className="contact-memory-header">
                    <div className="field-label">
                      <History size={16} />
                      <span>تاریخچه ذخیره‌شده</span>
                    </div>
                    <button className="mini-action" type="button" onClick={() => refreshHistory()} disabled={historyLoading}>
                      <RefreshCw className={historyLoading ? "animate-spin" : ""} size={14} />
                      <span>به‌روزرسانی</span>
                    </button>
                  </div>
                  {historyItems.length === 0 ? (
                    <div className="contact-empty-note">
                      فقط تحلیل‌هایی که در بخش حریم خصوصی گزینه تاریخچه حساب را بگیرند اینجا نمایش داده می‌شوند.
                    </div>
                  ) : (
                    <div className="history-list">
                      {historyItems.slice(0, 5).map((item) => (
                        <div className="history-row" key={item.id}>
                          <button
                            className="history-row-main"
                            type="button"
                            onClick={() => {
                              setFreeResult({
                                decode_id: item.id,
                                safety_label: item.safety_label,
                                prompt_version: "",
                                model_version: "",
                                free_output: item.free_output,
                                safety_output: null
                              });
                              setFreeResultGhost(false);
                              setPaidResult(item.paid_output ? { decode_id: item.id, credit_balance: credits, paid_output: item.paid_output } : null);
                              setStatus("تحلیل ذخیره‌شده باز شد.");
                            }}
                          >
                            <strong>{lensLabelFa(item.dominant_lens)} · {item.confidence_level}</strong>
                            <span>{item.message_preview || "بدون متن ذخیره‌شده"}</span>
                          </button>
                          <button
                            className="mini-action danger-action history-delete-action"
                            type="button"
                            onClick={() => handleDeleteHistoryItem(item.id)}
                            disabled={historyLoading}
                            aria-label="حذف تحلیل از تاریخچه"
                          >
                            <Trash2 size={14} />
                          </button>
                        </div>
                      ))}
                    </div>
                  )}
                  <button className="mini-action danger-action" type="button" onClick={handleDeleteStoredData} disabled={historyLoading}>
                    حذف همه داده‌های ذخیره‌شده
                  </button>
                </div>
              )}

              <button className="btn-primary btn-wide" onClick={handleFreeDecode} disabled={!message.trim() || loading}>
                {loading ? <RefreshCw className="animate-spin" size={18} /> : <Sparkles size={18} />}
                <span>برداشت پیام را رایگان ببینم</span>
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
                      <h3>قبل از پاسخ، این سه چیز را ببینید</h3>
                      <p>برداشت محتمل، ریسک جواب عجولانه و مسیر پاسخ کم‌تنش‌تر آماده است.</p>
                    </div>
                  </div>

                  {freeResult.safety_output && (
                    <div className="result-card safety-alert-card">
                      <div className="lens-header">
                        <span className="lens-badge danger">
                          <ShieldAlert size={14} /> {freeResult.safety_output.warning_title}
                        </span>
                        <span className="confidence-badge">اولویت: {freeResult.safety_output.priority}</span>
                      </div>
                      <h3>اول ایمنی، بعد پاسخ</h3>
                      <p>{freeResult.safety_output.recommendation}</p>
                      <div className="reply-bubble">{freeResult.safety_output.suggested_reply}</div>
                    </div>
                  )}

                  {freeResult.free_output && (
                    <>
                      <VisualSignals output={freeResult.free_output} />

                      {freeResultGhost && (
                        <div className="result-card ghost-result-card">
                          <h3>
                            <ShieldCheck size={14} /> این تحلیل در حالت شبح بود
                          </h3>
                          <p>متن و خروجی در تاریخچه ذخیره نشده است. اگر پاسخ کامل بسازید، همان پاسخ هم ذخیره نمی‌شود و فقط ۱ اعتبار مصرف می‌شود.</p>
                        </div>
                      )}

                      <div className="result-card hero-result-card">
                        <div className="lens-header">
                          <span className="lens-badge">
                            <Glasses size={14} />
                            <span>{freeResult.free_output.dominant_lens.fa}</span>
                          </span>
                        <span className="confidence-badge">میزان اطمینان: {freeResult.free_output.confidence}</span>
                        </div>
                        <h3>برداشت محتمل اصلی</h3>
                        {freeResult.free_output.message_focus && (
                          <div className="reply-badge">{freeResult.free_output.message_focus}</div>
                        )}
                        <p>{freeResult.free_output.dominant_lens_explanation}</p>
                        {freeResult.free_output.personalization_note && (
                          <p>{freeResult.free_output.personalization_note}</p>
                        )}
                      </div>

                      <div className="result-card">
                        <h3>
                          <Activity size={14} /> چرا این برداشت محتمل است؟
                        </h3>
                        <p>{freeResult.free_output.why_this_lens}</p>
                      </div>

                      <div className="result-card">
                        <h3>
                          <HeartHandshake size={14} /> نیاز یا نگرانی پشت پیام
                        </h3>
                        <p>{freeResult.free_output.likely_underlying_need}</p>
                      </div>

                      <div className="result-card warning-card">
                        <h3>
                          <Flame size={14} /> اگر عجولانه جواب دهید چه می‌شود؟
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
                          <Scale size={14} /> برداشت جایگزین را هم ببینید
                        </h3>
                        <p>{freeResult.free_output.alternative_read}</p>
                      </div>

                      {freeResult.free_output.privacy_warning && (
                        <div className="result-card danger-card">
                          <h3>
                            <ShieldAlert size={14} /> نکته حریم خصوصی
                          </h3>
                          <p>{freeResult.free_output.privacy_warning}</p>
                        </div>
                      )}

                      {!freeResultGhost && (
                        <div className="feedback-box">
                          <span>این تحلیل چقدر به چیزی که حس می‌کردید نزدیک بود؟</span>
                          <div className="feedback-buttons">
                            {["خیلی نزدیک بود", "تا حدی کمک کرد", "کمی سطحی بود", "اشتباه بود"].map((rating) => (
                              <button className="feedback-btn" key={rating} onClick={() => handleFeedback(rating)}>
                                {rating}
                              </button>
                            ))}
                          </div>
                        </div>
                      )}

                      {!paidResult && (
                        <div className="premium-lock-card">
                          <div className="premium-lock-header">
                            <div className="premium-lock-icon">
                              <Award size={24} />
                            </div>
                            <div className="premium-lock-details">
                              <span>قدم بعدی، اختیاری</span>
                              <h3>پاسخ قابل کپی بسازید: نرم، قاطع، کوتاه</h3>
                              <p>{freeResultGhost
                                ? "تحلیل اولیه رایگان است. پاسخ‌های آماده در حالت شبح ذخیره نمی‌شوند و ۱ اعتبار مصرف می‌کنند."
                                : "تحلیل اولیه رایگان است. ساخت پاسخ‌های آماده برای همین پیام ۱ اعتبار مصرف می‌کند."
                              }</p>
                            </div>
                          </div>

                          {!token ? (
                            <div className="auth-grid">
                              <div className="auth-title">
                                <LockKeyhole size={16} />
                                <span>شماره را وارد کنید تا ۵ اعتبار هدیه فعال شود</span>
                              </div>
                              <div className="auth-row">
                                <input
                                  type="tel"
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
                                    placeholder="کد ورود"
                                    value={otp}
                                    onChange={(event) => setOtp(event.target.value)}
                                  />
                                  <button className="btn-primary btn-compact" onClick={handleVerify}>
                                    ورود و فعال‌سازی اعتبار
                                  </button>
                                </div>
                              )}
                              <div className="auth-row">
                                <input
                                  type="text"
                                  placeholder="کد معرفی دارید؟ اختیاری"
                                  value={referralCode}
                                  onChange={(event) => setReferralCode(event.target.value.toUpperCase())}
                                />
                              </div>
                              <Link className="auth-free-link" href="/signup">
                                <UserPlus size={15} />
                                <span>جزئیات حساب و کد معرفی را ببینم</span>
                              </Link>
                            </div>
                          ) : (
                            <div className="auth-actions-group">
                              <button className="btn-secondary" onClick={handleBuyCredits}>
                                <CreditCard size={16} /> ۵ اعتبار بگیرم
                              </button>
                              <button className="btn-primary" onClick={handlePaidDecode} disabled={credits < 1 || loading}>
                                {loading ? <RefreshCw className="animate-spin" size={16} /> : <Sparkles size={16} />}
                                <span>پاسخ‌های قابل ارسال را بساز</span>
                              </button>
                            </div>
                          )}
                          {token && myReferral && (
                            <div className="contact-empty-note">
                              کد معرفی شما: <strong>{myReferral.referral_code}</strong> · هر شماره جدید با این کد، {myReferral.reward_credits} اعتبار برای شما فعال می‌کند.
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
                        <span>پاسخ‌های آماده، قابل ویرایش و ارسال</span>
                      </div>

                      <div className="result-card">
                        <h3>خلاصه عمیق‌تر قبل از ارسال</h3>
                        <p>{paidResult.paid_output.deep_read}</p>
                        {paidResult.paid_output.personalization_note && (
                          <p>{paidResult.paid_output.personalization_note}</p>
                        )}
                      </div>

                      {paidResult.paid_output.reply_options.map((reply) => (
                        <div className="reply-option-card" key={reply.label}>
                          <div className="reply-badge">{reply.label}</div>
                          <div className="reply-bubble">{reply.text}</div>
                          <div className="reply-why">
                            <strong>چرا احتمالاً کم‌ریسک‌تر است:</strong> {reply.why_it_works}
                          </div>
                          {reply.reaction_prediction && (
                            <div className="reaction-simulator">
                              <MessageCircle size={14} />
                              <div>
                                <strong>شبیه‌ساز واکنش</strong>
                                <span>{reply.reaction_prediction}</span>
                              </div>
                            </div>
                          )}
                          {!freeResultGhost && (
                            <button className="mini-action selected-reply-action" type="button" onClick={() => handleSelectedReply(reply.label)}>
                              این گزینه را انتخاب کردم
                            </button>
                          )}
                          <button className="btn-secondary copy-btn" onClick={() => handleCopy(reply.text, reply.label)}>
                            {copiedIndex === reply.label ? (
                              <>
                                <Check size={14} />
                                <span>کپی شد</span>
                              </>
                            ) : (
                              <>
                                <Copy size={14} />
                                <span>این پاسخ را کپی کنم</span>
                              </>
                            )}
                          </button>
                        </div>
                      ))}

                      <div className="result-card danger-card">
                        <h3>
                          <ShieldAlert size={14} /> کلماتی که ممکن است تنش را بیشتر کنند
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
                        <span>اگر یکی از پاسخ‌ها را فرستادید، نتیجه چه شد؟</span>
                        <div className="feedback-buttons">
                          <button className="feedback-btn" onClick={() => handleFeedback("paid", "تنش کمتر شد", 1)}>
                            تنش کمتر شد
                          </button>
                          <button className="feedback-btn" onClick={() => handleFeedback("paid", "طرف بهتر توضیح داد", 1)}>
                            طرف بهتر توضیح داد
                          </button>
                          <button className="feedback-btn" onClick={() => handleFeedback("paid", "دعوا بیشتر شد", 4)}>
                            تنش بیشتر شد
                          </button>
                          <button className="feedback-btn" onClick={() => handleFeedback("paid", "هنوز نفرستادم")}>
                            هنوز نفرستاده‌ام
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
                  <h3>پیامی دارید که قبل از جواب دادن مکث می‌خواهد؟</h3>
                  <p>متن را وارد کنید تا برداشت محتمل، ریسک سوءتفاهم و مسیر پاسخ کم‌تنش‌تر را ببینید.</p>
                </div>
              )}
            </div>
          </div>
        </div>
      </section>
    </main>
  );
}

type FreeOutput = NonNullable<FreeDecodeResponse["free_output"]>;

const lensMeta = {
  dopamine: { label: "هدف و کنترل", color: "#8a3ffc" },
  oxytocin: { label: "امنیت و اعتماد", color: "#1192e8" },
  serotonin: { label: "شأن و احترام", color: "#009d9a" }
} as const;

function VisualSignals({ output }: { output: FreeOutput }) {
  const lensMix = output.lens_mix ?? defaultLensMix(output.dominant_lens.key);
  const toneStress = output.tone_stress ?? { label: "مبهم", intensity: 35 };

  return (
    <div className="visual-signals">
      <div className="result-card radar-card">
        <div className="visual-title">
          <Radar size={16} />
          <h3>رادار سه لنز</h3>
        </div>
        <LensDonut mix={lensMix} dominantKey={output.dominant_lens.key} />
      </div>

      <div className="result-card tone-card">
        <div className="visual-title">
          <Activity size={16} />
          <h3>دماسنج لحن</h3>
        </div>
        <div className="tone-meter">
          <div className="tone-meter-track">
            <div className="tone-meter-fill" style={{ width: `${toneStress.intensity}%` }} />
          </div>
          <div className="tone-meter-meta">
            <strong>{toneStress.label}</strong>
            <span>{toneStress.intensity}٪ فشار مکالمه</span>
          </div>
        </div>
      </div>
    </div>
  );
}

function LensDonut({ mix, dominantKey }: { mix: Required<FreeOutput>["lens_mix"]; dominantKey: string }) {
  const dopamine = mix.dopamine;
  const oxytocin = mix.oxytocin;
  const serotonin = mix.serotonin;
  const slices = [
    { key: "dopamine", value: dopamine, offset: 0 },
    { key: "oxytocin", value: oxytocin, offset: -dopamine },
    { key: "serotonin", value: serotonin, offset: -(dopamine + oxytocin) }
  ] as const;

  return (
    <div className="lens-donut-layout">
      <svg className="lens-donut" viewBox="0 0 140 140" role="img" aria-label="رادار سهم لنزها">
        <circle className="lens-donut-bg" cx="70" cy="70" r="48" pathLength="100" />
        {slices.map((slice) => (
          <circle
            key={slice.key}
            className="lens-donut-slice"
            cx="70"
            cy="70"
            r="48"
            pathLength="100"
            stroke={lensMeta[slice.key].color}
            strokeDasharray={`${slice.value} ${100 - slice.value}`}
            strokeDashoffset={slice.offset}
          />
        ))}
        <text x="70" y="66" textAnchor="middle" className="lens-donut-number">
          {mix[dominantKey as keyof typeof mix]}%
        </text>
        <text x="70" y="84" textAnchor="middle" className="lens-donut-label">
          لنز غالب
        </text>
      </svg>

      <div className="lens-mix-list">
        {(Object.keys(lensMeta) as Array<keyof typeof lensMeta>).map((key) => (
          <div className="lens-mix-row" key={key}>
            <span className="lens-dot" style={{ backgroundColor: lensMeta[key].color }} />
            <span>{lensMeta[key].label}</span>
            <strong>{mix[key]}٪</strong>
          </div>
        ))}
      </div>
    </div>
  );
}

function defaultLensMix(dominantKey: string): Required<FreeOutput>["lens_mix"] {
  if (dominantKey === "dopamine") {
    return { dopamine: 70, oxytocin: 15, serotonin: 15 };
  }
  if (dominantKey === "serotonin") {
    return { dopamine: 15, oxytocin: 15, serotonin: 70 };
  }
  return { dopamine: 15, oxytocin: 70, serotonin: 15 };
}

function lensLabelFa(value: string) {
  return ({
    dopamine: "هدف و کنترل",
    oxytocin: "امنیت و اعتماد",
    serotonin: "شأن و احترام"
  } as Record<string, string>)[value] ?? value;
}
