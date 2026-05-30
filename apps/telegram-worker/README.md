# Message Decoder Telegram Worker

Cloudflare Workers version of the Telegram bot for a zero-VPS MVP.

## Setup

```bash
cd apps/telegram-worker
npx wrangler d1 create message-decoder-telegram
```

Put the returned `database_id` in `wrangler.toml`, then run:

```bash
npx wrangler d1 migrations apply message-decoder-telegram --remote
npx wrangler secret put TELEGRAM_BOT_TOKEN
npx wrangler secret put TELEGRAM_WEBHOOK_SECRET
npx wrangler deploy
```

Set the Telegram webhook:

```bash
curl -X POST "https://api.telegram.org/bot$TELEGRAM_BOT_TOKEN/setWebhook" \
  -H "Content-Type: application/json" \
  -d '{"url":"https://YOUR_WORKER.YOUR_SUBDOMAIN.workers.dev/webhook","secret_token":"YOUR_TELEGRAM_WEBHOOK_SECRET","allowed_updates":["message","callback_query"]}'
```

This Worker is intentionally lightweight. It stores Telegram sessions, users, credits, and decodes in D1, and uses a local rule/template engine for free and paid outputs. Payment and the full FastAPI core can be connected later.
