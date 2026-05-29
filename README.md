# Message Decoder by NeuroLens

Persian-first MVP scaffold for decoding emotionally ambiguous, tense, cold, aggressive, or professional messages before replying.

## Structure

- `specification.md`: مادر محصول
- `development_plan.md`: برنامه اجرایی
- `docs/PRODUCT_TECH_BUSINESS_OVERVIEW.md`: مستند جامع محصول، فنی و منطق کسب‌وکار
- `apps/api`: FastAPI backend
- `apps/web`: Next.js RTL web app

## Local API

```bash
cd apps/api
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload
```

API docs: `http://127.0.0.1:8000/docs`

## Local Web

```bash
cd apps/web
npm install
npm run dev
```

Web app: `http://localhost:3000`

## MVP Defaults

- AI provider is a deterministic mock pipeline by default.
- OTP provider is dev/mock by default; production can use SMS.ir with `OTP_PROVIDER=smsir`.
- Payment provider is a Zarinpal-shaped sandbox adapter.

For SMS.ir OTP, set `SMSIR_API_KEY`. With `SMSIR_METHOD=auto`, the app uses `SMSIR_TEMPLATE_ID` and `send/verify` when a verified template is configured; otherwise it uses `SMSIR_LINE_NUMBER` and bulk send with `SMSIR_MESSAGE_TEMPLATE`. Sent and failed SMS attempts are recorded in `sms_send_logs` for later accounting.
