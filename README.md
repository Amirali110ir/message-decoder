# Message Decoder by NeuroLens

Persian-first MVP scaffold for decoding emotionally ambiguous, tense, cold, aggressive, or professional messages before replying.

## Structure

- `specification.md`: مادر محصول
- `development_plan.md`: برنامه اجرایی
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
- OTP provider is dev/mock and returns `123456` unless configured.
- Payment provider is a Zarinpal-shaped sandbox adapter.

