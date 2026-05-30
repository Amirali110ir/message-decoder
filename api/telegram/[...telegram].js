const DEFAULT_WORKER_BASE_URL = "https://message-decoder-telegram.shabestani-am.workers.dev";

export default async function handler(request, response) {
  if (request.method !== "POST") {
    response.status(405).json({ ok: false, error: "method_not_allowed" });
    return;
  }

  const parts = Array.isArray(request.query.telegram)
    ? request.query.telegram
    : [request.query.telegram].filter(Boolean);
  if (parts.length < 2 || !String(parts[0]).startsWith("bot")) {
    response.status(404).json({ ok: false, error: "bad_telegram_path" });
    return;
  }

  const workerBaseUrl = (process.env.TELEGRAM_WORKER_BASE_URL || DEFAULT_WORKER_BASE_URL).replace(/\/$/, "");
  const workerUrl = `${workerBaseUrl}/${parts.map(encodeURIComponent).join("/")}`;

  try {
    const upstream = await fetch(workerUrl, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify(request.body || {}),
    });
    const text = await upstream.text();
    response
      .status(upstream.status)
      .setHeader("Content-Type", upstream.headers.get("content-type") || "application/json")
      .send(text);
  } catch (error) {
    response.status(502).json({
      ok: false,
      error: "telegram_relay_failed",
      detail: error instanceof Error ? error.message : "unknown",
    });
  }
}
