"use client";

import {
  ArrowLeft,
  EyeOff,
  MessageSquareText,
  Radar,
  ShieldCheck,
  Sparkles,
  Zap,
} from "lucide-react";
import { useRouter } from "next/navigation";
import { useEffect, useState } from "react";

const LENS_DATA = [
  {
    key: "dopamine",
    fa: "هدف و کنترل",
    color: "var(--dopamine)",
    soft: "var(--dopamine-soft)",
    desc: "حول هدف و کنترل می‌چرخد — چه کسی تصمیم می‌گیرد، چه کسی کوتاه می‌آید.",
  },
  {
    key: "oxytocin",
    fa: "امنیت و اعتماد",
    color: "var(--oxytocin)",
    soft: "var(--oxytocin-soft)",
    desc: "حول امنیت و اعتماد — «آیا کنارم هستی؟ آیا مهمم؟»",
  },
  {
    key: "serotonin",
    fa: "شأن و احترام",
    color: "var(--serotonin)",
    soft: "var(--serotonin-soft)",
    desc: "حول شأن و احترام — «جایگاهم دیده می‌شود یا نه؟»",
  },
];

function ScrHead() {
  return (
    <div className="scr-head">
      <div className="brand-mini">
        <div className="brand-mark">
          <MessageSquareText size={18} />
        </div>
        <div>
          <div className="brand-name">Message Decoder</div>
          <div className="brand-sub">تحلیل پیام، قبل از پاسخ</div>
        </div>
      </div>
    </div>
  );
}

function ObShell({
  step,
  onSkip,
  onNext,
  nextLabel,
  children,
}: {
  step: number;
  onSkip: () => void;
  onNext: () => void;
  nextLabel: React.ReactNode;
  children: React.ReactNode;
}) {
  return (
    <div className="onb-stage">
      <div className="onb-card stagger">
        <ScrHead />
        <div className="onb-top" style={{ marginBottom: 8 }}>
          <div className="ob-dots">
            {[0, 1, 2].map((i) => (
              <i key={i} className={i === step ? "on" : ""} />
            ))}
          </div>
          <span className="kicker">{step + 1} از ۳</span>
        </div>

        {children}

        <div className="onb-spacer" />

        <div className="onb-foot">
          <button className="btn btn-primary btn-block" onClick={onNext}>
            {nextLabel}
          </button>
          <button
            className="btn btn-link"
            style={{ alignSelf: "center", marginTop: 4 }}
            onClick={onSkip}
          >
            رد کردن معرفی
          </button>
        </div>
      </div>
    </div>
  );
}

/* ---- Screen 1: The Promise ---- */
function Step1({ onNext, onSkip }: { onNext: () => void; onSkip: () => void }) {
  return (
    <ObShell
      step={0}
      onSkip={onSkip}
      onNext={onNext}
      nextLabel={
        <>
          شروع <ArrowLeft size={18} />
        </>
      }
    >
      <div style={{ marginTop: 54, display: "flex", flexDirection: "column", gap: 22 }}>
        <span className="pill" style={{ alignSelf: "flex-start" }}>
          <Radar size={15} style={{ color: "var(--primary-strong)" }} />
          یک مکثِ کوتاه، قبل از جواب
        </span>
        <h1 className="display">
          قبل از جواب دادن،
          <br />
          بفهم پشتِ پیام
          <br />
          چه خبر است.
        </h1>
        <p className="body" style={{ maxWidth: 300 }}>
          یک نفس عمیق. ما کمکت می‌کنیم آرام‌تر ببینی چه چیزی واقعاً گفته شده — تا از روی هیجان جواب ندهی.
        </p>
      </div>
    </ObShell>
  );
}

/* ---- Screen 2: Three Lenses ---- */
function Step2({ onNext, onSkip }: { onNext: () => void; onSkip: () => void }) {
  return (
    <ObShell
      step={1}
      onSkip={onSkip}
      onNext={onNext}
      nextLabel={
        <>
          بعدی <ArrowLeft size={18} />
        </>
      }
    >
      <div style={{ marginTop: 30, display: "flex", flexDirection: "column", gap: 14 }}>
        <h1 className="title-lg">پیام را از سه لنز می‌بینیم</h1>
        <p className="body" style={{ marginBottom: 6 }}>
          هر گفتگو ترکیبی از این سه است. ما نسبتشان را تخمین می‌زنیم — نه یک حکم قطعی.
        </p>
        <div className="stack">
          {LENS_DATA.map((l) => (
            <div
              key={l.key}
              className="card"
              style={{
                display: "flex",
                gap: 13,
                alignItems: "flex-start",
                borderColor: "var(--border)",
              }}
            >
              <span
                style={{
                  display: "block",
                  width: 30,
                  height: 30,
                  borderRadius: "50%",
                  background: l.soft,
                  border: `1.75px solid ${l.color}`,
                  flex: "0 0 auto",
                  marginTop: 2,
                }}
              />
              <div>
                <div
                  className="title"
                  style={{ fontSize: 16, color: l.color, fontFamily: "var(--font-head)", fontWeight: 700 }}
                >
                  {l.fa}
                </div>
                <p className="small" style={{ marginTop: 3 }}>
                  {l.desc}
                </p>
              </div>
            </div>
          ))}
        </div>
      </div>
    </ObShell>
  );
}

/* ---- Screen 3: Privacy + Instant Start ---- */
function Step3({ onFinish, onSkip }: { onFinish: () => void; onSkip: () => void }) {
  return (
    <ObShell
      step={2}
      onSkip={onSkip}
      onNext={onFinish}
      nextLabel={
        <>
          <Sparkles size={18} /> اولین پیام را تحلیل کن
        </>
      }
    >
      <div style={{ marginTop: 40, display: "flex", flexDirection: "column", gap: 18 }}>
        <span style={{ color: "var(--primary-strong)" }}>
          <ShieldCheck size={40} />
        </span>
        <h1 className="title-lg">بدون ورود، بدون ردپا</h1>
        <p className="body">
          تحلیلِ اولیه رایگان است و بدون ساختِ حساب کار می‌کند. هر زمان خواستی، حالت شبح را روشن کن تا هیچ چیز ذخیره نشود.
        </p>
        <div className="stack">
          <div className="note">
            <span className="ni">
              <Sparkles size={16} />
            </span>
            <span>اولین تحلیل، همین حالا و رایگان — بدون شماره و رمز.</span>
          </div>
          <div className="note">
            <span className="ni">
              <EyeOff size={16} />
            </span>
            <span>
              <b style={{ color: "var(--ink)" }}>حالت شبح:</b> متن و نتیجه در تاریخچه ذخیره نمی‌شود.
            </span>
          </div>
          <div className="note">
            <span className="ni">
              <Zap size={16} />
            </span>
            <span>
              بعداً اگر خواستی پاسخ کامل و قابل‌ارسال بسازی، فقط شماره موبایل کافی است.
            </span>
          </div>
        </div>
      </div>
    </ObShell>
  );
}

export default function OnboardingPage() {
  const router = useRouter();
  const [step, setStep] = useState(0);

  useEffect(() => {
    if (typeof window !== "undefined" && localStorage.getItem("md-onboarded")) {
      router.replace("/decoder");
    }
  }, [router]);

  function finish() {
    localStorage.setItem("md-onboarded", "1");
    router.push("/decoder");
  }

  function skip() {
    localStorage.setItem("md-onboarded", "1");
    router.push("/decoder");
  }

  if (step === 0) return <Step1 onNext={() => setStep(1)} onSkip={skip} />;
  if (step === 1) return <Step2 onNext={() => setStep(2)} onSkip={skip} />;
  return <Step3 onFinish={finish} onSkip={skip} />;
}
