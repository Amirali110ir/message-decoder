import crypto from "crypto";

const DEFAULT_WORKER_BASE_URL = "https://message-decoder-telegram.shabestani-am.workers.dev";

function applyCors(response) {
  response.setHeader("Access-Control-Allow-Origin", "*");
  response.setHeader("Access-Control-Allow-Methods", "POST, OPTIONS");
  response.setHeader("Access-Control-Allow-Headers", "Content-Type");
}

export default async function handler(request, response) {
  applyCors(response);
  if (request.method === "OPTIONS") {
    response.status(204).end();
    return;
  }

  if (request.method !== "POST") {
    response.status(405).json({ ok: false, error: "method_not_allowed" });
    return;
  }

  const payload = request.body?.payload;
  if (!payload || !payload.chat_id || !payload.text || !payload.signature) {
    response.status(400).json({ ok: false, error: "invalid_payload" });
    return;
  }

  const bridgeSecret = process.env.TELEGRAM_BRIDGE_SECRET;
  const botToken = process.env.TELEGRAM_BOT_TOKEN;
  if (!bridgeSecret || !botToken) {
    response.status(200).json({ ok: false, skipped: true });
    return;
  }

  // Verify HMAC signature
  const expectedMessage = `${payload.chat_id}|${payload.text}`;
  const expectedSignature = crypto
    .createHmac("sha256", bridgeSecret)
    .update(expectedMessage)
    .digest("hex");

  if (payload.signature !== expectedSignature) {
    response.status(401).json({ ok: false, error: "invalid_signature" });
    return;
  }

  const workerBaseUrl = (process.env.TELEGRAM_WORKER_BASE_URL || DEFAULT_WORKER_BASE_URL).replace(/\/$/, "");

  try {
    const sendResponse = await fetch(`${workerBaseUrl}/bot${botToken}/sendMessage`, {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ chat_id: payload.chat_id, text: payload.text, parse_mode: "HTML" }),
    });
    response.status(200).json({ ok: sendResponse.ok, delivered: sendResponse.ok });
  } catch (error) {
    response.status(200).json({
      ok: false,
      delivered: false,
      error: error instanceof Error ? error.message : "unknown",
    });
  }
}
