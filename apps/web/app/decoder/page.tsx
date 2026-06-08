"use client";

import {
  Activity,
  AlertCircle,
  ArrowLeft,
  Award,
  BookOpenCheck,
  BrainCircuit,
  Check,
  Copy,
  CreditCard,
  EyeOff,
  Fingerprint,
  Glasses,
  History,
  Layers,
  LockKeyhole,
  LogIn,
  MessageCircle,
  MessageSquareCode,
  MessageSquareText,
  Radar,
  RefreshCw,
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
import { useEffect, useRef, useState } from "react";
import type { Contact, DecodeHistoryItem, RelationshipThermometer } from "../../lib/api";
import type { ToneTarget, ToneEditResponse, BeforeSendResponse } from "../../lib/api";
import { faNum } from "../../lib/format";
import {
  beforeSendCheck,
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
  toneEdit,
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

const toneOptions: [ToneTarget, string][] = [
  ["softer", "نرم‌تر"],
  ["firmer", "قاطع‌تر"],
  ["shorter", "کوتاه‌تر"],
  ["warmer", "گرم‌تر"],
  ["formal", "رسمی‌تر"]
];

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

// Mirror the backend hard caps (T1.7 / T10.1): max 5 recent messages, 500 chars each.
// The thread keeps speaker info; we fold it into each line so the AI sees who said what.
function threadToRecentMessages(thread: { who: string; text: string }[]): string[] | undefined {
  const lines = thread
    .slice(0, 5)
    .map((m) => `${m.who === "me" ? "من" : "او"}: ${m.text.trim().slice(0, 500)}`)
    .filter(Boolean);
  return lines.length ? lines : undefined;
}

// Episode builder — chat-thread composer matching the design prototype.
function EpisodeBuilder({
  thread,
  setThread,
  epBackground,
  setEpBackground,
  epBehavior,
  setEpBehavior
}: {
  thread: { who: string; text: string }[];
  setThread: (t: { who: string; text: string }[]) => void;
  epBackground: string;
  setEpBackground: (v: string) => void;
  epBehavior: string;
  setEpBehavior: (v: string) => void;
}) {
  const [who, setWho] = useState("them");
  const [draft, setDraft] = useState("");
  const full = thread.length >= 5;
  const add = () => {
    const t = draft.trim();
    if (!t || full) return;
    setThread([...thread, { who, text: t.slice(0, 500) }]);
    setDraft("");
  };
  return (
    <div className="ep-wrap">
      <div className="ep-head">
        <span className="ep-mark"><Layers size={18} /></span>
        <div>
          <h4>کلِ ماجرا را تعریف کن</h4>
          <p>یک پیام معمولاً وسطِ یک ماجراست. هرچه بیشتر بدهی، تحلیل دقیق‌تر می‌شود — همه اختیاری.</p>
        </div>
      </div>

      <div className="ep-block">
        <div className="field-label"><MessageCircle size={15} /> گفت‌وگوی منتهی به این پیام</div>
        <div className="ep-thread">
          {thread.length === 0 ? (
            <div className="ep-empty">چند پیامِ آخر را اضافه کن تا ترتیبِ ماجرا روشن شود.</div>
          ) : (
            thread.map((m, i) => (
              <div key={i} className={`ep-msg ${m.who}`}>
                <span className="ep-who">{m.who === "me" ? "من" : "او"}</span>
                {m.text}
                <button
                  className="ep-del"
                  type="button"
                  onClick={() => setThread(thread.filter((_, idx) => idx !== i))}
                  aria-label="حذف"
                >
                  ×
                </button>
              </div>
            ))
          )}
        </div>
        {!full && (
          <div className="ep-composer">
            <div className="ep-speaker">
              {([["them", "او"], ["me", "من"]] as const).map(([v, l]) => (
                <button key={v} type="button" className={`${v} ${who === v ? "on" : ""}`} onClick={() => setWho(v)}>{l}</button>
              ))}
            </div>
            <input
              className="field"
              value={draft}
              onChange={(e) => setDraft(e.target.value)}
              onKeyDown={(e) => { if (e.key === "Enter") { e.preventDefault(); add(); } }}
              placeholder={who === "me" ? "چیزی که تو گفتی…" : "چیزی که او گفت…"}
            />
            <button className="ep-add" type="button" onClick={add} disabled={!draft.trim()} aria-label="افزودن پیام">
              <ArrowLeft size={17} />
            </button>
          </div>
        )}
        <div className="ep-count">{faNum(thread.length)} از ۵ پیام {full ? "· پُر شد" : ""}</div>
      </div>

      <div className="ep-block">
        <div className="field-label"><History size={15} /> پیشینهٔ ماجرا — قبلش چه شد؟</div>
        <textarea
          className="field"
          value={epBackground}
          onChange={(e) => setEpBackground(e.target.value)}
          placeholder="ماجرا از کجا شروع شد و چه اتفاقی افتاد…"
          style={{ minHeight: 72 }}
          maxLength={1000}
        />
      </div>

      <div className="ep-block">
        <div className="field-label"><Users size={15} /> رفتارِ طرف مقابل — این اواخر چطور بوده؟</div>
        <textarea
          className="field"
          value={epBehavior}
          onChange={(e) => setEpBehavior(e.target.value)}
          placeholder="مثلاً: سرد شده، دیر جواب می‌دهد، زود می‌رنجد…"
          style={{ minHeight: 64 }}
          maxLength={1000}
        />
      </div>
    </div>
  );
}

export default function DecoderPage() {
  const [message, setMessage] = useState("");
  const [relationship, setRelationship] = useState("romantic");
  const [goal, setGoal] = useState("avoid_needy");
  const [context, setContext] = useState("");
  const [episodeBackground, setEpisodeBackground] = useState("");
  const [theirBehavior, setTheirBehavior] = useState("");
  const [thread, setThread] = useState<{ who: string; text: string }[]>([]);
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
  const [showSecondaryResults, setShowSecondaryResults] = useState(false);
  const [status, setStatus] = useState("");
  const [error, setError] = useState("");
  const [copiedIndex, setCopiedIndex] = useState<string | null>(null);
  const [toneEdits, setToneEdits] = useState<Record<string, ToneEditResponse>>({});
  const [toneLoading, setToneLoading] = useState<string | null>(null);
  const [draftText, setDraftText] = useState("");
  const [beforeSendResult, setBeforeSendResult] = useState<BeforeSendResponse | null>(null);
  const [beforeSendLoading, setBeforeSendLoading] = useState(false);
  const messageInputRef = useRef<HTMLTextAreaElement>(null);
  const feedbackRef = useRef<HTMLDivElement>(null);

  // Bring status/error feedback into view when it changes, so it isn't missed
  // far above the control that triggered it (T18).
  useEffect(() => {
    if (!status && !error) return;
    feedbackRef.current?.scrollIntoView({ behavior: "smooth", block: "nearest" });
  }, [status, error]);

  useEffect(() => {
    const searchParams = new URLSearchParams(window.location.search);
    const prefillMsg = searchParams.get("msg");
    if (prefillMsg) setMessage(decodeURIComponent(prefillMsg));

    // Demo seed for previewing the result/paid UI without a live backend.
    // Dev-only: never injects sample data in a production build.
    if (process.env.NODE_ENV !== "production" && searchParams.get("demo") === "loading") {
      setLoading(true);
      return;
    }
    if (process.env.NODE_ENV !== "production" && searchParams.get("demo")) {
      setMessage(DEMO_SAMPLE.message);
      setRelationship("romantic");
      setGoal("avoid_needy");
      if (searchParams.get("demo") === "safety") {
        setFreeResult({
          ...DEMO_FREE,
          safety_label: "high_risk",
          free_output: null,
          safety_output: {
            warning_title: "این پیام نشانه‌های نگران‌کننده دارد",
            priority: "بالا",
            recommendation: "از روی یک پیام نمی‌شود قطعی قضاوت کرد، اما این متن می‌تواند نشانهٔ یک حالِ خطرناک باشد. اینجا هدف، محافظت است نه ترساندن.",
            suggested_reply: "من اینجام و برام مهمی. می‌تونیم همین الان با هم حرف بزنیم؟ تنها نیستی."
          }
        });
      } else {
        setFreeResult(DEMO_FREE);
      }
      if (searchParams.get("demo") === "paid") setPaidResult(DEMO_PAID);
      setStatus("نمونهٔ پیش‌نمایش تحلیل.");
    }

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
    if (!message.trim()) {
      setError("متن پیام را وارد کنید تا تحلیل شروع شود.");
      messageInputRef.current?.focus();
      return;
    }
    setError("");
    setLoading(true);
    setShowSecondaryResults(false);
    setStatus("داریم پیام را از نظر لحن، ریسک و نیاز احتمالی می‌خوانیم...");
    setPaidResult(null);
    try {
      const result = await freeDecode({
        message_text: message,
        relationship_type: relationship as never,
        user_goal: goal as never,
        optional_context: context || undefined,
        episode_background: episodeBackground.trim() || undefined,
        their_behavior: theirBehavior.trim() || undefined,
        recent_messages: threadToRecentMessages(thread),
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
            // Ghost paid has no structured episode field, so fold it into context.
            optional_context: [
              context.trim(),
              episodeBackground.trim() && `پیشینه/رابطه: ${episodeBackground.trim()}`,
              theirBehavior.trim() && `رفتار طرف مقابل: ${theirBehavior.trim()}`,
              thread.length > 0 && `چند پیامِ آخر: ${threadToRecentMessages(thread)!.join(" | ")}`
            ].filter(Boolean).join("\n") || undefined
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

  async function handleToneEdit(replyLabel: string, replyText: string, tone: ToneTarget) {
    if (!token) {
      setError("برای ویرایش لحن، اول وارد شوید.");
      return;
    }
    setError("");
    setToneLoading(`${replyLabel}:${tone}`);
    try {
      const res = await toneEdit(token, {
        reply_text: replyText,
        target_tone: tone,
        relationship_type: relationship as never,
        user_goal: goal as never,
        original_message: message || undefined
      });
      setToneEdits((prev) => ({ ...prev, [replyLabel]: res }));
    } catch (err) {
      setError(err instanceof Error ? err.message : "ویرایش لحن انجام نشد.");
    } finally {
      setToneLoading(null);
    }
  }

  async function handleBeforeSend() {
    if (!token) {
      setError("برای بررسی پیش از ارسال، اول وارد شوید.");
      return;
    }
    if (!draftText.trim()) {
      setError("متنی که می‌خواهید بفرستید را وارد کنید.");
      return;
    }
    setError("");
    setBeforeSendLoading(true);
    try {
      const res = await beforeSendCheck(token, {
        draft_text: draftText.trim(),
        relationship_type: relationship as never,
        user_goal: goal as never,
        original_message: message || undefined
      });
      setBeforeSendResult(res);
    } catch (err) {
      setError(err instanceof Error ? err.message : "بررسی پیش از ارسال انجام نشد.");
    } finally {
      setBeforeSendLoading(false);
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
            <button
              type="button"
              className={`ghost-toggle-compact${ghostMode ? " on" : ""}`}
              onClick={() => setGhostMode((v) => !v)}
              title="حالت شبح: متن و نتیجه ذخیره نمی‌شود"
            >
              <EyeOff size={14} />
              <span className="ghost-label-short">{ghostMode ? "شبح: روشن" : "حالت شبح"}</span>
            </button>
            {token && (
              <a href="#history-panel" className="iconbtn" title="تاریخچه تحلیل‌ها">
                <History size={18} />
              </a>
            )}
            {token ? (
              <>
                <div className="account-badge">
                  <User size={14} />
                  <span>{phone}</span>
                </div>
                <div className="credit-badge">
                  <Zap size={14} />
                  <span>{faNum(credits)} اعتبار</span>
                </div>
              </>
            ) : null}
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
                  ref={messageInputRef}
                  value={message}
                  onChange={(event) => setMessage(event.target.value)}
                  placeholder="مثلاً: باشه، هر جور راحتی. معلومه که اصلاً برات مهم نیست."
                />
              </div>

              <div className="field-group">
                <label className="field-label">
                  <Users size={16} />
                  <span>رابطه با چه کسی؟</span>
                </label>
                <div className="chip-row">
                  {relationshipOptions.map(([value, label]) => (
                    <button
                      type="button"
                      key={value}
                      className={`chip ${relationship === value ? "active" : ""}`}
                      onClick={() => setRelationship(value)}
                    >
                      {label}
                    </button>
                  ))}
                </div>
              </div>

              <div className="field-group">
                <label className="field-label">
                  <Target size={16} />
                  <span>از این پاسخ چه می‌خواهی؟</span>
                </label>
                <div className="chip-row">
                  {goalOptions.map(([value, label]) => (
                    <button
                      type="button"
                      key={value}
                      className={`chip ${goal === value ? "active" : ""}`}
                      onClick={() => setGoal(value)}
                    >
                      {label}
                    </button>
                  ))}
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

                  <EpisodeBuilder
                    thread={thread}
                    setThread={setThread}
                    epBackground={episodeBackground}
                    setEpBackground={setEpisodeBackground}
                    epBehavior={theirBehavior}
                    setEpBehavior={setTheirBehavior}
                  />

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
                          {contact.name} · {faNum(contact.interaction_count)} تحلیل
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
                          <span>روند تدافعی {relationshipThermometer.defensive_trend > 0 ? "+" : ""}{faNum(relationshipThermometer.defensive_trend)}</span>
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
                <div id="history-panel" className="history-memory-card">
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

              <button className="btn-primary btn-wide" onClick={handleFreeDecode} disabled={loading}>
                {loading ? <RefreshCw className="animate-spin" size={18} /> : <Sparkles size={18} />}
                <span>برداشت پیام را رایگان ببینم</span>
              </button>
              <p className="small" style={{ textAlign: "center", marginTop: 10, color: "var(--ink-faint)" }}>
                تحلیلِ اول رایگان است{ghostMode ? " · حالت شبح روشن است" : ""}
              </p>
            </div>

            <div className="panel-card results-panel">
              <div ref={feedbackRef} aria-live="polite" aria-atomic="true">
                {status && (
                  <div className="toast-msg toast-success" role="status">
                    <Check size={16} />
                    <span>{status}</span>
                  </div>
                )}
                {error && (
                  <div className="toast-msg toast-error" role="alert">
                    <AlertCircle size={16} />
                    <span>{error}</span>
                  </div>
                )}
              </div>

              {loading && !freeResult ? (
                <AnalyzingState />
              ) : freeResult ? (
                <div className="results-container">
                  <div className="panel-title">
                    <Radar size={19} />
                    <div>
                      <h3>قبل از پاسخ، این سه چیز را ببینید</h3>
                      <p>برداشت محتمل، ریسک جواب عجولانه و مسیر پاسخ کم‌تنش‌تر آماده است.</p>
                    </div>
                  </div>

                  {freeResult.safety_output && (
                    <div className="safety-state">
                      <span style={{ color: "var(--danger)" }}><ShieldAlert size={40} /></span>
                      <h1 className="title-lg" style={{ marginTop: 6 }}>{freeResult.safety_output.warning_title}</h1>
                      <p className="ds-pill" style={{ marginTop: 4, color: "#e08178", borderColor: "rgba(184,69,59,0.3)", background: "var(--danger-soft)" }}>اولویت: {freeResult.safety_output.priority}</p>
                      <p className="body-ink" style={{ marginTop: 10 }}>{freeResult.safety_output.recommendation}</p>

                      <div className="ds-card stack-card" style={{ background: "var(--surface)", borderColor: "rgba(184,69,59,0.3)" }}>
                        <div className="card-h" style={{ fontSize: 15 }}><MessageCircle size={16} style={{ color: "var(--oxytocin)" }} /> اگر خواستی چیزی بگویی</div>
                        <div className="reply-text" style={{ marginTop: 8, marginBottom: 0, fontSize: 16 }}>{freeResult.safety_output.suggested_reply}</div>
                      </div>

                      <div className="ds-note" style={{ marginTop: 14, borderColor: "rgba(184,69,59,0.3)", background: "var(--danger-soft)" }}>
                        <span className="ni" style={{ color: "#e08178" }}><ShieldCheck size={16} /></span>
                        <span style={{ color: "var(--ink)" }}>از روی یک پیام نمی‌شود قطعی قضاوت کرد. اگر خطرِ فوری حس می‌کنی، او را تنها نگذار و در صورت لزوم از یک فردِ مورد اعتماد یا خط کمک کمک بگیر — خط ملی اورژانس اجتماعی ۱۲۳.</span>
                      </div>
                    </div>
                  )}

                  {freeResult.free_output && (() => {
                    const fo = freeResult.free_output;
                    const mix = fo.lens_mix ?? defaultLensMix(fo.dominant_lens.key);
                    const tone = fo.tone_stress ?? { label: "مبهم", intensity: 35 };
                    return (
                    <>
                      {freeResultGhost && (
                        <div className="ds-card stack-card">
                          <div className="card-h"><EyeOff size={17} style={{ color: "var(--serotonin)" }} /> این تحلیل در حالت شبح بود</div>
                          <p className="body">متن و خروجی در تاریخچه ذخیره نشده است. اگر پاسخ کامل بسازید، همان پاسخ هم ذخیره نمی‌شود و فقط ۱ اعتبار مصرف می‌شود.</p>
                        </div>
                      )}

                      {freeResult.clarifying_question && (
                        <div className="ds-card stack-card">
                          <div className="card-h"><MessageCircle size={17} style={{ color: "var(--primary-strong)" }} /> برای تحلیل دقیق‌تر، یک سؤال</div>
                          <p className="body">{freeResult.clarifying_question}</p>
                          <button
                            type="button"
                            className="btn btn-ghost btn-sm btn-block"
                            style={{ marginTop: 12 }}
                            onClick={() => {
                              setShowAdvancedInputs(true);
                              messageInputRef.current?.scrollIntoView({ behavior: "smooth" });
                            }}
                          >
                            جوابش را در «قبلش چه شد؟» بنویس و دوباره تحلیل کن
                          </button>
                        </div>
                      )}

                      <div className="hero-card stack" style={{ gap: 14 }}>
                        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", gap: 8 }}>
                          <LensChip lens={fo.dominant_lens.key} label={fo.dominant_lens.fa} />
                          <span className="small">اطمینان: {fo.confidence}</span>
                        </div>
                        {fo.message_focus && (
                          <div className="reply-tag" style={{ margin: 0, background: "var(--oxytocin-soft)", color: "var(--oxytocin)" }}>{fo.message_focus}</div>
                        )}
                        <p className="body-ink">{fo.dominant_lens_explanation}</p>
                        {fo.personalization_note && <p className="body">{fo.personalization_note}</p>}
                      </div>

                      {fo.situation_arc && (
                        <div className="ds-card stack-card" style={{ borderColor: "var(--border-hi)" }}>
                          <div className="card-h"><BookOpenCheck size={17} style={{ color: "var(--primary-strong)" }} /> قوسِ ماجرا — کجا اوضاع چرخید</div>
                          <p className="body-ink">{fo.situation_arc}</p>
                        </div>
                      )}

                      <div className="ds-card stack-card">
                        <div className="card-h"><Radar size={17} style={{ color: "var(--primary-strong)" }} /> رادارِ سه لنز</div>
                        <LensDonut mix={mix} dominantKey={fo.dominant_lens.key} />
                        <hr className="ds-hr" style={{ margin: "16px 0 14px" }} />
                        <div className="card-h" style={{ marginBottom: 12 }}><Activity size={17} style={{ color: "var(--primary-strong)" }} /> دماسنجِ لحن</div>
                        <ToneMeter value={tone.intensity} label={tone.label} caption={`${faNum(tone.intensity)}٪ فشارِ مکالمه`} />
                      </div>

                      {fo.insight_line && (
                        <div className="ds-card stack-card">
                          <div className="card-h"><Sparkles size={17} style={{ color: "var(--dopamine)" }} /> نکته‌ای که شاید ندیده باشی</div>
                          <p className="body-ink">{fo.insight_line}</p>
                        </div>
                      )}

                      <div className="ds-card warn stack-card">
                        <div className="card-h"><AlertCircle size={17} style={{ color: "var(--dopamine)" }} /> اگر عجولانه جواب بدهی</div>
                        <p className="body-ink">{fo.conversation_risk}</p>
                      </div>

                      <div className="ds-card good stack-card">
                        <div className="card-h"><ShieldCheck size={17} style={{ color: "var(--success)" }} /> مسیرِ پاسخِ کم‌تنش‌تر</div>
                        <p className="body-ink">{fo.recommended_direction}</p>
                      </div>

                      <button
                        className="btn btn-ghost btn-block btn-sm"
                        style={{ marginTop: 14 }}
                        type="button"
                        onClick={() => setShowSecondaryResults((v) => !v)}
                      >
                        {showSecondaryResults ? "بستن جزئیات" : "جزئیاتِ بیشتر: چرا، نیازِ پنهان، برداشتِ جایگزین"}
                      </button>

                      {showSecondaryResults && (
                        <div className="stack" style={{ marginTop: 12 }}>
                          <div className="ds-card stack-card">
                            <div className="card-h" style={{ fontSize: 15 }}>چرا این برداشت محتمل است؟</div>
                            <p className="body">{fo.why_this_lens}</p>
                          </div>

                          <div className="ds-card stack-card">
                            <div className="card-h" style={{ fontSize: 15 }}>نیاز یا نگرانی پشت پیام</div>
                            <p className="body">{fo.likely_underlying_need}</p>
                          </div>

                          <div className="ds-card stack-card">
                            <div className="card-h" style={{ fontSize: 15 }}>برداشتِ جایگزین</div>
                            <p className="body">{fo.alternative_read}</p>
                          </div>

                          {fo.privacy_warning && (
                            <div className="ds-card danger stack-card">
                              <div className="card-h" style={{ fontSize: 15 }}>نکته حریم خصوصی</div>
                              <p className="body">{fo.privacy_warning}</p>
                            </div>
                          )}
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
                                  inputMode="tel"
                                  autoComplete="tel"
                                  placeholder="09123456789"
                                  value={phone}
                                  onChange={(event) => setPhone(event.target.value)}
                                />
                                <button className="btn-secondary" onClick={handleOtp}>
                                  <LogIn size={15} /> گرفتن کد ورود
                                </button>
                              </div>

                              {otpSent && (
                                <div className="enter" style={{ display: "flex", flexDirection: "column", gap: 10 }}>
                                  <div style={{ position: "relative" }}>
                                    <div className="seg" style={{ direction: "ltr", justifyContent: "center", padding: 8, gap: 8, background: "transparent", border: "none" }}>
                                      {[0, 1, 2, 3].map((i) => (
                                        <div key={i} style={{
                                          width: 46, height: 54, borderRadius: 12,
                                          background: "var(--surface-alt)",
                                          border: `1.5px solid ${i < otp.length ? "var(--primary)" : "var(--border)"}`,
                                          display: "grid", placeItems: "center",
                                          fontFamily: "var(--font-head)", fontWeight: 800, fontSize: 22,
                                          color: "var(--ink)", transition: "border-color 0.15s"
                                        }}>
                                          {otp[i] ? faNum(otp[i]) : ""}
                                        </div>
                                      ))}
                                    </div>
                                    <input
                                      type="tel"
                                      inputMode="numeric"
                                      autoComplete="one-time-code"
                                      maxLength={4}
                                      value={otp}
                                      onChange={(e) => setOtp(e.target.value.replace(/\D/g, "").slice(0, 4))}
                                      aria-label="کد ورود ۴ رقمی"
                                      style={{ position: "absolute", inset: 0, opacity: 0, cursor: "text", width: "100%", height: "100%" }}
                                    />
                                  </div>
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
                              <p className="small" style={{ textAlign: "center", color: "var(--ink-faint)", marginTop: 2 }}>
                                بدونِ فشار. هر وقت آماده بودی. شماره فقط برای نگه‌داشتنِ اعتبار است.
                              </p>
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
                              کد معرفی شما: <strong>{myReferral.referral_code}</strong> · هر شماره جدید با این کد، {faNum(myReferral.reward_credits)} اعتبار برای شما فعال می‌کند.
                            </div>
                          )}
                        </div>
                      )}
                    </>
                    );
                  })()}

                  {paidResult && (
                    <div className="deep-results">
                      <div className="deep-results-title">
                        <Award size={20} />
                        <span>پاسخ‌های آماده، قابل ویرایش و ارسال</span>
                      </div>

                      <div className="ds-card stack-card">
                        <div className="card-h"><Glasses size={17} style={{ color: "var(--oxytocin)" }} /> خلاصهٔ عمیق‌تر</div>
                        <p className="body-ink">{paidResult.paid_output.deep_read}</p>
                        {paidResult.paid_output.personalization_note && (
                          <p className="body">{paidResult.paid_output.personalization_note}</p>
                        )}
                      </div>

                      <div className="stack-lg">
                      {paidResult.paid_output.reply_options.map((reply) => (
                        <div className="reply-card" key={reply.label}>
                          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center" }}>
                            <span className="reply-tag" style={{ margin: 0 }}><MessageCircle size={14} /> {reply.label}</span>
                            {reply.reaction_forecast && <RiskPill level={reply.reaction_forecast.risk_level} />}
                          </div>
                          <div className="reply-text" style={{ marginTop: 12 }}>{reply.text}</div>
                          {(reply.reaction_forecast || reply.reaction_prediction) && (
                            <div className="reaction">
                              <span style={{ color: "var(--primary-strong)", flex: "0 0 auto", marginTop: 1 }}><Radar size={16} /></span>
                              <div className="r-body">
                                <strong>شبیه‌سازِ واکنش</strong>
                                {reply.reaction_forecast ? (
                                  <>
                                    <span>{reply.reaction_forecast.likely_reaction} </span>
                                    <span className="faint">{reply.reaction_forecast.reason}</span>
                                  </>
                                ) : (
                                  <span>{reply.reaction_prediction}</span>
                                )}
                              </div>
                            </div>
                          )}
                          {reply.why_it_works && (
                            <p className="small" style={{ marginBottom: 12 }}>
                              <strong style={{ color: "var(--ink)" }}>چرا کم‌ریسک‌تر است: </strong>{reply.why_it_works}
                            </p>
                          )}
                          <div className="reply-actions">
                            <button className="btn btn-soft btn-sm" style={{ flex: 1 }} onClick={() => handleCopy(reply.text, reply.label)}>
                              {copiedIndex === reply.label ? (<><Check size={15} /> کپی شد</>) : (<><Copy size={15} /> کپی</>)}
                            </button>
                            {!freeResultGhost && (
                              <button className="btn btn-ghost btn-sm" type="button" onClick={() => handleSelectedReply(reply.label)}>
                                این را انتخاب کردم
                              </button>
                            )}
                          </div>
                          <div className="tone-row">
                            <span className="tlabel">لحن:</span>
                            {toneOptions.map(([tone, label]) => (
                              <button
                                key={tone}
                                type="button"
                                className="tone-btn"
                                disabled={toneLoading === `${reply.label}:${tone}`}
                                onClick={() => handleToneEdit(reply.label, reply.text, tone)}
                              >
                                {toneLoading === `${reply.label}:${tone}` ? "..." : label}
                              </button>
                            ))}
                          </div>

                          {toneEdits[reply.label] && (
                            <div className="reply-text" style={{ marginTop: 12, marginBottom: 0 }}>
                              <div className="reply-tag" style={{ margin: "0 0 10px" }}>نسخهٔ {toneEdits[reply.label].tone_label}</div>
                              {toneEdits[reply.label].text}
                              <button
                                className="btn btn-soft btn-sm btn-block"
                                style={{ marginTop: 12 }}
                                onClick={() => handleCopy(toneEdits[reply.label].text, `${reply.label}-tone`)}
                              >
                                {copiedIndex === `${reply.label}-tone` ? (<><Check size={15} /> کپی شد</>) : (<><Copy size={15} /> کپی نسخه ویرایش‌شده</>)}
                              </button>
                            </div>
                          )}
                        </div>
                      ))}
                      </div>

                      <div className="ds-card danger stack-card">
                        <div className="card-h"><AlertCircle size={17} style={{ color: "var(--danger)" }} /> کلماتی که تنش را بیشتر می‌کنند</div>
                        <div className="word-tags" style={{ marginTop: 4 }}>
                          {paidResult.paid_output.words_to_avoid.map((word, i) => (
                            <span className="word-tag" key={i}>
                              {word}
                            </span>
                          ))}
                        </div>
                      </div>

                      <div className="ds-card before-send-card stack-card">
                        <div className="card-h"><ShieldCheck size={17} style={{ color: "var(--primary-strong)" }} /> بررسی قبل از ارسال</div>
                        <p className="small" style={{ marginBottom: 10 }}>متنی که می‌خواهی بفرستی را اینجا بگذار تا ریسک واکنش منفی و نکات قابل بهبودش را قبل از ارسال ببینی.</p>
                        <textarea
                          className="before-send-input"
                          value={draftText}
                          onChange={(event) => setDraftText(event.target.value)}
                          placeholder="متنی که می‌خواهید بفرستید..."
                          rows={3}
                        />
                        <button
                          className="btn-secondary"
                          type="button"
                          disabled={beforeSendLoading}
                          onClick={handleBeforeSend}
                        >
                          {beforeSendLoading ? "در حال بررسی..." : "قبل از ارسال بررسی کن"}
                        </button>
                        {beforeSendResult && (
                          <div className={`before-send-result risk-${beforeSendResult.risk_level === "زیاد" ? "high" : beforeSendResult.risk_level === "متوسط" ? "mid" : "low"}`}>
                            <div className="before-send-meta">
                              <strong>ریسک: {beforeSendResult.risk_level}</strong>
                              <span>{faNum(beforeSendResult.risk_score)}٪</span>
                            </div>
                            <p>{beforeSendResult.summary}</p>
                            {beforeSendResult.flags.length > 0 && (
                              <ul className="before-send-list">
                                {beforeSendResult.flags.map((flag, i) => (
                                  <li key={`flag-${i}`}>{flag}</li>
                                ))}
                              </ul>
                            )}
                            {beforeSendResult.suggestions.length > 0 && (
                              <ul className="before-send-list before-send-suggestions">
                                {beforeSendResult.suggestions.map((suggestion, i) => (
                                  <li key={`sug-${i}`}>{suggestion}</li>
                                ))}
                              </ul>
                            )}
                            {beforeSendResult.improved_text && (
                              <div className="tone-edit-result">
                                <div className="tone-edit-result-badge">نسخه کم‌ریسک‌تر پیشنهادی</div>
                                <div className="reply-bubble">{beforeSendResult.improved_text}</div>
                                <button
                                  className="btn-secondary copy-btn"
                                  onClick={() => handleCopy(beforeSendResult.improved_text || "", "before-send-improved")}
                                >
                                  {copiedIndex === "before-send-improved" ? (
                                    <>
                                      <Check size={14} />
                                      <span>کپی شد</span>
                                    </>
                                  ) : (
                                    <>
                                      <Copy size={14} />
                                      <span>کپی نسخه پیشنهادی</span>
                                    </>
                                  )}
                                </button>
                              </div>
                            )}
                          </div>
                        )}
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
type LensKey = "dopamine" | "oxytocin" | "serotonin";

// Canonical lens mapping (matches the design prototype).
const lensMeta: Record<LensKey, { label: string; color: string }> = {
  dopamine: { label: "هدف و کنترل", color: "var(--dopamine)" },
  oxytocin: { label: "امنیت و اعتماد", color: "var(--oxytocin)" },
  serotonin: { label: "شأن و احترام", color: "var(--serotonin)" }
};
const LENS_ORDER: LensKey[] = ["dopamine", "oxytocin", "serotonin"];

// Aperture-ring lens motif: abstract shape inside a shared diaphragm ring.
function ApertureGlyph({ lens, size = 20 }: { lens: string; size?: number }) {
  const inner: Record<string, React.ReactNode> = {
    dopamine: <path d="M12 7.5 13.8 11l3.7.6-2.7 2.6.6 3.7L12 16.2 8.6 18l.6-3.7L6.5 11.6l3.7-.6L12 7.5Z" />,
    oxytocin: <path d="M12 16.5s-4-2.6-4-5.4A2.2 2.2 0 0 1 12 9.6a2.2 2.2 0 0 1 4 1.5c0 2.8-4 5.4-4 5.4Z" />,
    serotonin: (
      <>
        <circle cx="12" cy="11.5" r="2.4" />
        <path d="M9 16.5c.8-1.2 1.8-1.8 3-1.8s2.2.6 3 1.8" />
      </>
    )
  };
  return (
    <svg
      className="aperture"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth={1.75}
      strokeLinecap="round"
      strokeLinejoin="round"
      aria-hidden="true"
    >
      <circle cx="12" cy="12" r="9.2" />
      <path d="M12 2.8 17 5.5M21.2 12l-2.7 4.8M12 21.2 7 18.5M2.8 12l2.7-4.8" opacity="0.55" />
      {inner[lens] ?? inner.oxytocin}
    </svg>
  );
}

function LensChip({ lens, label }: { lens: string; label: string }) {
  return (
    <span className={`lens-chip ${lens}`}>
      <ApertureGlyph lens={lens} size={20} />
      <span>{label}</span>
    </span>
  );
}

function RiskPill({ level }: { level: string }) {
  const map: Record<string, [string, string]> = {
    low: ["کم‌ریسک", "risk-low"],
    mid: ["ریسکِ متوسط", "risk-mid"],
    high: ["پرریسک", "risk-high"],
    کم: ["کم‌ریسک", "risk-low"],
    متوسط: ["ریسکِ متوسط", "risk-mid"],
    زیاد: ["پرریسک", "risk-high"]
  };
  const [text, cls] = map[level] ?? map.mid;
  return <span className={`risk-pill ${cls}`}>{text}</span>;
}

function ToneMeter({ value, label, caption }: { value: number; label: string; caption: string }) {
  return (
    <div>
      <div className="ds-meter-track">
        <div className="ds-meter-fill warm" style={{ width: `${value}%` }} />
      </div>
      <div className="ds-meter-meta">
        <strong>{label}</strong>
        <span>{caption}</span>
      </div>
    </div>
  );
}

function LensDonut({ mix, dominantKey }: { mix: Record<LensKey, number>; dominantKey: string }) {
  const C = 2 * Math.PI * 53;
  let acc = 0;
  return (
    <div className="donut-wrap">
      <svg className="donut" viewBox="0 0 140 140" role="img" aria-label="رادار سهم لنزها">
        <circle className="donut-bg" cx="70" cy="70" r="53" />
        {LENS_ORDER.map((key) => {
          const frac = (mix[key] || 0) / 100;
          const dash = `${frac * C} ${C - frac * C}`;
          const off = -acc * C;
          acc += frac;
          return (
            <circle
              key={key}
              className="donut-slice"
              cx="70"
              cy="70"
              r="53"
              stroke={lensMeta[key].color}
              strokeDasharray={dash}
              strokeDashoffset={off}
            />
          );
        })}
        <g className="donut-center">
          <text className="donut-num" x="70" y="68" textAnchor="middle">
            {faNum(mix[dominantKey as LensKey] ?? 0)}٪
          </text>
          <text className="donut-cap" x="70" y="86" textAnchor="middle">
            لنز غالب
          </text>
        </g>
      </svg>
      <div className="mix-list">
        {LENS_ORDER.map((key) => (
          <div className="mix-row" key={key}>
            <span className="ldot" style={{ background: lensMeta[key].color }} />
            <span className="mname">{lensMeta[key].label}</span>
            <strong>{faNum(mix[key] || 0)}٪</strong>
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

// ---- Analyzing "breath" moment (matches the design prototype) ----
const ANALYZING_LINES = [
  "دارم پیام را در زمینهٔ رابطه می‌بینم…",
  "لحن و نیازِ زیرین را می‌سنجم…",
  "ریسکِ جوابِ عجولانه را تخمین می‌زنم…"
];

function AnalyzingState() {
  const [i, setI] = useState(0);
  useEffect(() => {
    const t = setInterval(() => setI((v) => (v + 1) % ANALYZING_LINES.length), 1100);
    return () => clearInterval(t);
  }, []);
  return (
    <div className="analyzing-state">
      <div className="breath-orb"><div className="core" /></div>
      <div className="analyzing-copy">
        <h2 className="title">یک نفس بکش</h2>
        <p className="body" key={i}>{ANALYZING_LINES[i]}</p>
      </div>
    </div>
  );
}

// ---- Demo seed (preview only; matches the design prototype sample) ----
const DEMO_SAMPLE = { message: "نه بابا، مهم نیست. باشه یه وقت دیگه. می‌دونم سرت شلوغه." };

const DEMO_FREE: FreeDecodeResponse = {
  decode_id: "demo",
  safety_label: "none",
  prompt_version: "",
  model_version: "",
  clarifying_question: null,
  free_output: {
    dominant_lens: { fa: "امنیت و اعتماد", en: "Oxytocin", key: "oxytocin" },
    dominant_lens_explanation:
      "این جمله بیش از آنکه واقعاً «بی‌خیال» باشد، یک عقب‌نشینیِ مودبانه است. «می‌دونم سرت شلوغه» نیمه‌تعارف است و زیرش این پیام را دارد: حس می‌کنم دیگر در اولویتت نیستم.",
    why_this_lens:
      "کلیدواژه‌ها («مهم نیست»، «یه وقت دیگه»، «سرت شلوغه») حول جایگاه و اولویت در رابطه‌اند، نه یک خواستهٔ مشخصِ عملی.",
    message_focus: "بزرگواریِ ظاهری روی دلخوریِ نادیده‌گرفته‌شدن",
    personalization_note: null,
    secondary_lenses: [],
    lens_mix: { dopamine: 12, oxytocin: 52, serotonin: 36 },
    tone_stress: { label: "تسلیمِ دلخور", intensity: 56 },
    likely_underlying_need:
      "نیاز به مطمئن‌شدن از اینکه هنوز برایت ارزش و اولویت دارد؛ ترسِ زیرین: شاید برایت مهم نیست.",
    conversation_risk:
      "اگر فقط بپذیری («باشه، یه وقت دیگه») یا توضیحِ طولانیِ گرفتاری‌ات را بدهی، آن را تأییدِ بی‌اهمیتی می‌خواند و دفعهٔ بعد دیگر پیش‌قدم نمی‌شود.",
    recommended_direction:
      "دلخوریِ پشتِ تعارف را به‌رسمیت بشناس و خودت یک زمانِ مشخص و قطعی پیشنهاد بده؛ ابتکار را به دست بگیر، نه عذرخواهیِ طولانی.",
    confidence: "نسبتاً مطمئن",
    alternative_read:
      "ممکن است واقعاً درگیر باشد و این جمله فقط یک تعارفِ سادهٔ بی‌منظور باشد، نه گلایه.",
    insight_line:
      "«مهم نیست» اینجا یعنی «مهم بود». وقتی کسی توقعش را پایین می‌آورد، معمولاً برای این است که دیگر نمی‌خواهد ناامید شود.",
    situation_arc:
      "از یک جابه‌جاییِ سادهٔ قرار شروع شده، ولی چون چند بار تکرار شده، حالا به حسِ «انگار اولویت نیستم» رسیده.",
    privacy_warning: null,
    cta: ""
  },
  safety_output: null
};

const DEMO_PAID: PaidDecodeResponse = {
  decode_id: "demo",
  credit_balance: 4,
  paid_output: {
    deep_read:
      "زیرِ این «مهم نیست»، یک درخواست هست: «بهم نشون بده هنوز برات در اولویتم». بهترین پاسخ، حرف نیست — یک پیشنهادِ زمانِ مشخص و قطعی است که ابتکار را خودت به دست بگیری.",
    personalization_note: null,
    reply_options: [
      {
        label: "گرم + زمانِ قطعی",
        text: "راست می‌گی، چند بار عقب افتاد و این اصلاً منصفانه نیست. خودم یه روزِ قطعی می‌ذارم که این‌بار حتماً بشه — پنجشنبه عصر خوبه برات؟",
        why_it_works: "هم دلخوری را می‌پذیرد، هم با پیشنهادِ زمانِ مشخص ثابت می‌کند که اولویت است.",
        reaction_forecast: { likely_reaction: "احتمالاً لحنش باز می‌شود و قرار را قطعی می‌کند.", reason: "چون به‌جای تعارف، یک اقدامِ واقعی دید.", risk_level: "کم" }
      },
      {
        label: "صادق و کوتاه",
        text: "می‌دونم چند بار جور نشد و حق داری دلخور باشی. تو برام مهمی؛ بذار این‌بار خودم برنامه‌ریزیش کنم.",
        why_it_works: "مسئولیت را می‌پذیرد و ابتکار را به‌دست می‌گیرد، بدون توجیهِ طولانی.",
        reaction_forecast: { likely_reaction: "ممکن است اول کوتاه جواب دهد، ولی توقعِ پایین‌آمده‌اش بالا می‌رود.", reason: "اطمینان هست، اما هنوز زمانِ مشخص نگذاشته‌ای.", risk_level: "متوسط" }
      },
      {
        label: "ساده و بی‌تعارف",
        text: "نگو مهم نیست، چون برای من مهمه. بیا یه وقتی که واقعاً برای جفتمون جور باشه پیدا کنیم و این‌بار نذاریم بپره.",
        why_it_works: "تعارف را رد می‌کند و رابطه را در اولویت می‌گذارد.",
        reaction_forecast: { likely_reaction: "شاید کمی جا بخورد، ولی حس می‌کند دیده شده.", reason: "نشان می‌دهد عقب‌افتادن از بی‌اهمیتی نبوده.", risk_level: "متوسط" }
      }
    ],
    words_to_avoid: ["همیشه همینه", "تو هم که هیچ‌وقت", "گیر نده", "بی‌خیال", "حالا یه باره دیگه"],
    safe_opening_line: "",
    copy_ready_reply: "",
    attribution_reply: null,
    follow_up_question: ""
  }
};

function lensLabelFa(value: string) {
  return ({
    dopamine: "هدف و کنترل",
    oxytocin: "امنیت و اعتماد",
    serotonin: "شأن و احترام"
  } as Record<string, string>)[value] ?? value;
}
