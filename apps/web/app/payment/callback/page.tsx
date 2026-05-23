"use client";

import Link from "next/link";
import { Suspense, useEffect, useState } from "react";
import { useSearchParams } from "next/navigation";
import { CheckCircle2, Loader2, XCircle } from "lucide-react";
import { verifyPayment } from "../../../lib/api";

export default function PaymentCallbackPage() {
  return (
    <Suspense fallback={<PaymentShell state="loading" message="در حال بررسی نتیجه پرداخت..." />}>
      <PaymentCallbackInner />
    </Suspense>
  );
}

function PaymentCallbackInner() {
  const searchParams = useSearchParams();
  const [state, setState] = useState<"loading" | "success" | "error">("loading");
  const [message, setMessage] = useState("در حال بررسی نتیجه پرداخت...");

  useEffect(() => {
    async function verify() {
      const paymentId = searchParams.get("payment_id") || window.localStorage.getItem("message-decoder-pending-payment");
      const authority = searchParams.get("Authority");
      const status = searchParams.get("Status");
      const token = window.localStorage.getItem("message-decoder-token");

      if (!paymentId || !token) {
        setState("error");
        setMessage("پرداخت پیدا نشد. دوباره از صفحه تحلیل اعتبار بگیرید.");
        return;
      }
      if (status && status.toUpperCase() !== "OK") {
        setState("error");
        setMessage("پرداخت توسط درگاه تایید نشد یا لغو شد.");
        return;
      }
      try {
        const result = await verifyPayment(token, paymentId, { authority, status: status || "OK" });
        window.localStorage.removeItem("message-decoder-pending-payment");
        setState("success");
        setMessage(`پرداخت تایید شد. اعتبار فعلی شما ${result.credit_balance} است.`);
      } catch (err) {
        setState("error");
        setMessage(err instanceof Error ? err.message : "تایید پرداخت انجام نشد.");
      }
    }
    verify();
  }, [searchParams]);

  return <PaymentShell state={state} message={message} />;
}

function PaymentShell({ state, message }: { state: "loading" | "success" | "error"; message: string }) {
  const Icon = state === "loading" ? Loader2 : state === "success" ? CheckCircle2 : XCircle;
  return (
    <main className="page decoder-page">
      <header className="topbar">
        <div className="shell topbar-inner">
          <Link className="brand" href="/" aria-label="Message Decoder">
            <div className="brand-logo">MD</div>
            <div className="brand-text">
              <span className="brand-title">Message Decoder</span>
              <span className="brand-subtitle">نتیجه پرداخت</span>
            </div>
          </Link>
          <Link className="nav-login" href="/decoder">
            برگشت به تحلیل
          </Link>
        </div>
      </header>
      <section className="decoder-section">
        <div className="shell payment-callback-card">
          <Icon className={state === "loading" ? "animate-spin" : ""} size={32} />
          <h1>{state === "success" ? "اعتبار اضافه شد" : state === "error" ? "پرداخت تایید نشد" : "بررسی پرداخت"}</h1>
          <p>{message}</p>
          <Link className="btn-primary" href="/decoder">
            ادامه در Message Decoder
          </Link>
        </div>
      </section>
    </main>
  );
}
