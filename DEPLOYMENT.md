# استقرار روی Liara و Vercel

## مسیر پیشنهادی کم‌هزینه: یک app واحد

برای شروع، فقط یک app لازم است که هم FastAPI را اجرا می‌کند و هم خروجی static وب را از همان backend سرو می‌کند.

App پیشنهادی:

- Name: `message-decoder-py`
- Platform: Docker
- Port: `8000`
- Plan: `small-g2`
- Feature bundle: Bronze
- Network: `message-decoder-net`

Deploy:

```bash
liara deploy \
  --app message-decoder-py \
  --path . \
  --dockerfile Dockerfile \
  --port 8000 \
  --build-arg NEXT_PUBLIC_API_URL= \
  --message "deploy single app"
```

در این حالت `NEXT_PUBLIC_API_URL` خالی می‌ماند تا frontend همان origin سرور را صدا بزند.

## مسیر پیشنهادی برای تجربه بهتر frontend: Web روی Vercel + API روی Liara

اگر می‌خواهی UI از CDN و pipeline آماده Vercel استفاده کند، backend را روی Liara نگه دار و فقط `apps/web` را روی Vercel ببر. فایل `vercel.json` ریشه پروژه برای همین حالت آماده شده است:

- Install Command: `npm ci`
- Build Command: `npm run build:web`
- Output Directory: `apps/web/out`

چون `apps/web/next.config.ts` روی `output: "export"` است، خروجی frontend کاملاً static ساخته می‌شود و Vercel همان `apps/web/out` را سرو می‌کند.

### Envهای Vercel

روی پروژه Vercel فقط این env لازم است:

```bash
NEXT_PUBLIC_API_URL=https://YOUR_LIARA_API_DOMAIN
TELEGRAM_WORKER_BASE_URL=https://message-decoder-telegram.shabestani-am.workers.dev
```

مقدار `YOUR_LIARA_API_DOMAIN` باید دامنه public اپ API روی Liara باشد، بدون slash آخر. مثال:

```bash
NEXT_PUBLIC_API_URL=https://message-decoder-py.liara.run
```

### Envهای Liara برای هماهنگی با Vercel

وقتی frontend روی Vercel است، روی app API در Liara این دو مقدار را با دامنه واقعی Vercel تنظیم کن:

```bash
ZARINPAL_CALLBACK_URL=https://YOUR_VERCEL_DOMAIN/payment/callback
CORS_ORIGINS=https://YOUR_VERCEL_DOMAIN,http://localhost:3000,http://127.0.0.1:3000
TELEGRAM_API_BASE_URL=https://YOUR_VERCEL_DOMAIN/api/telegram
TELEGRAM_API_BYPASS_SECRET=...
```

اگر از preview deployهای Vercel هم استفاده می‌کنی، دامنه preview را هم به `CORS_ORIGINS` اضافه کن. برای production بهتر است دامنه ثابت یا custom domain داشته باشی تا callback پرداخت و CORS پایدار بمانند.

### Deploy روی Vercel

از ریشه repo:

```bash
vercel
```

یا برای production:

```bash
vercel --prod
```

اگر در داشبورد Vercel پروژه را از Git وصل می‌کنی، root پروژه را همان ریشه repo بگذار؛ `vercel.json` خودش workspace درست را build می‌کند. فایل `.vercelignore` هم اضافه شده تا API، دیتابیس‌ها، خروجی‌های build قبلی و پوشه‌های نامرتبط وارد آپلود Vercel نشوند.

## مسیر دو app جدا

اگر بعداً بخواهیم frontend و backend جدا scale شوند، پروژه به دو app جدا روی Liara نیاز دارد:

1. `message-decoder-py` (Backend)
2. `message-decoder-web` (Frontend)

## 1. ورود به Liara

```bash
liara login
```

یا با API token:

```bash
liara deploy --api-token "$LIARA_API_TOKEN" ...
```

## 2. ساخت appها

از پنل Liara یا CLI دو app با platform Docker بساز.

## 3. Envهای API

روی app مربوط به API این envها را تنظیم کن:

```bash
AI_PROVIDER=openai_compatible
AI_API_BASE_URL=https://api.openai.com/v1
AI_API_KEY=...
AI_MODEL=gpt-4.1-mini
AI_FREE_MODEL=openai/gpt-5.4-nano
AI_PAID_MODEL=openai/gpt-5.4-mini
AI_MODEL_VERSION=gpt-4.1-mini
DATABASE_URL=sqlite:////data/message_decoder.db
OTP_PROVIDER=smsir
SMSIR_API_KEY=...
SMSIR_METHOD=auto
SMSIR_TEMPLATE_ID=...
SMSIR_PARAMETER_NAME=Code
SMSIR_LINE_NUMBER=300089931441
SMSIR_MESSAGE_TEMPLATE=رمزگشایی از خطوط پنهان پیام.\n\nکلید ورود به دکودر: {code}
# قالب تایید در پنل sms.ir باید یک پارامتر هم‌نام داشته باشد.
# نمونه متن قالب:
# رمزگشایی از خطوط پنهان پیام.
#
# کلید ورود به دکودر: #Code#
# اگر SMSIR_TEMPLATE_ID خالی باشد، auto با SMSIR_LINE_NUMBER ارسال عادی bulk انجام می‌دهد.
# همه تلاش‌های ارسال در جدول sms_send_logs ثبت می‌شوند.
DEV_OTP_CODE=123456
JWT_SECRET=change-this
ADMIN_TOKEN=change-this
ZARINPAL_MERCHANT_ID=...
ZARINPAL_CALLBACK_URL=https://YOUR_WEB_DOMAIN/payment/callback
CORS_ORIGINS=https://YOUR_WEB_DOMAIN,http://localhost:3000
```

اگر از API هوش مصنوعی Liara یا هر provider سازگار با OpenAI استفاده می‌کنی، `AI_API_BASE_URL`، `AI_API_KEY` و مدل‌ها را تنظیم کن. `AI_MODEL` برای سازگاری قدیمی باقی مانده؛ اگر `AI_FREE_MODEL` و `AI_PAID_MODEL` خالی باشند همان استفاده می‌شود.

## 4. Envهای Web

در build web باید API public URL ست شود:

```bash
NEXT_PUBLIC_API_URL=https://YOUR_API_DOMAIN
```

## 5. Deploy API

```bash
liara deploy \
  --app message-decoder-py \
  --path apps/api \
  --dockerfile Dockerfile \
  --port 8000 \
  --message "deploy api"
```

برای SQLite پایدار باید یک disk روی مسیر `/data` به app API وصل شود. برای production بهتر است PostgreSQL جایگزین SQLite شود.

## 6. Deploy Web

```bash
liara deploy \
  --app message-decoder-py \
  --path . \
  --dockerfile apps/web/Dockerfile \
  --port 3000 \
  --build-arg NEXT_PUBLIC_API_URL=https://YOUR_API_DOMAIN \
  --message "deploy web"
```

## ✅ OTP Setup Checklist (تولید)

اگر OTP نمی‌رسد، طبق این مراحل قدم به قدم بررسی کن:

### 1. انتخاب provider روی Liara

```bash
liara env --app message-decoder-py
# مطمئن شو OTP_PROVIDER روی smsir یا kavenegar تنظیم است (نه mock)
```

اگر `OTP_PROVIDER=mock` باشد، **هیچ SMS واقعی ارسال نمی‌شود** و کاربر فقط `dev_otp_code` می‌بیند.

### 2. envهای SMS.ir (اگر provider=smsir)

```bash
OTP_PROVIDER=smsir
SMSIR_API_KEY=<از پنل sms.ir>
SMSIR_METHOD=auto
SMSIR_TEMPLATE_ID=<شناسه قالب تایید‌شده>
SMSIR_PARAMETER_NAME=Code
SMSIR_LINE_NUMBER=<خط ارسال، مثل 300089931441>
```

تست curl:

```bash
curl -X POST https://message-decoder-py.liara.run/auth/request-otp \
  -H "Content-Type: application/json" \
  -d '{"phone":"09120000000"}'
```

اگر `502 ارسال پیامک ...`، `liara logs --app message-decoder-py | grep smsir` را چک کن. اگر `200 ok`، در جدول `sms_send_logs` رکورد جدید با `status=sent` ببین.

### 3. envهای Kavenegar (اگر provider=kavenegar)

```bash
OTP_PROVIDER=kavenegar
KAVENEGAR_API_KEY=<از پنل kavenegar>
KAVENEGAR_METHOD=verify_lookup
KAVENEGAR_TEMPLATE=<شناسه قالب تاییدشده>
# یا برای ارسال معمولی:
# KAVENEGAR_METHOD=send
# KAVENEGAR_SENDER=<خط ارسال>
```

### 4. Telegram OTP bridge (اختیاری)

اگر می‌خواهی کاربرانی که Telegram bot را وصل کرده‌اند، کد را داخل تلگرام هم بگیرند، **یک secret یکسان** در سه جا ست کن:

```bash
# Liara API
TELEGRAM_BRIDGE_SECRET=<random-strong-secret>
TELEGRAM_BOT_TOKEN=<bot token>

# Vercel project
TELEGRAM_BRIDGE_SECRET=<همان مقدار>
TELEGRAM_BOT_TOKEN=<همان bot token>
TELEGRAM_WORKER_BASE_URL=https://message-decoder-telegram.shabestani-am.workers.dev

# Cloudflare Worker (wrangler secret put)
wrangler secret put TELEGRAM_BRIDGE_SECRET   # همان مقدار
wrangler secret put TELEGRAM_BOT_TOKEN       # همان token
wrangler secret put LIARA_API_URL            # https://message-decoder-py.liara.run
```

**اگر secret خالی باشد یا بین سه جا تفاوت داشته باشد:** Telegram payload یا ساخته نمی‌شود (در log: `telegram_otp.skipped reason=bridge_secret_missing`) یا 401 از Vercel function می‌گیرد.

### 5. CORS

مطمئن شو دامنه Vercel در `CORS_ORIGINS` Liara آمده:

```bash
CORS_ORIGINS=https://YOUR_VERCEL_DOMAIN,https://message-decoder-py.liara.run,http://localhost:3000
```

بدون این، browser request به Liara را block می‌کند و کاربر فقط می‌بیند "ارتباط برقرار نشد".

### 6. بررسی log

```bash
liara logs --app message-decoder-py --since 10m | grep -E "otp\.|smsir|kavenegar|telegram_otp"
```

پیام‌های log کلیدی:

- `otp.request provider=smsir phone=091***00 production=True` → درخواست رسید
- `smsir.verify missing_api_key` → env پر نشده
- `smsir.verify rejected ... body={...}` → خطای provider، body کامل را چک کن
- `telegram_otp.skipped reason=user_not_linked` → کاربر هرگز bot را با شماره‌اش وصل نکرده

### 7. بررسی DB

```sql
SELECT phone, status, error_message, created_at
FROM sms_send_logs
ORDER BY created_at DESC
LIMIT 10;
```

اگر این جدول خالی است: provider اصلاً صدا زده نشده (احتمالاً mock یا env-mismatch).

---

## وضعیت فعلی

- AI واقعی آماده است و با env فعال می‌شود.
- OTP هنوز dev/mock است.
- Payment هنوز sandbox-shaped است و برای زرین‌پال واقعی باید adapter verify تکمیل شود.
- Liara CLI در این ماشین باید login شود تا deploy انجام شود.

## چالش‌های شبکه ملی (ایران) و راه‌حل‌ها (تجارب قطعی)
هنگام دپلوی برنامه روی سرورهای ایران لیارا (`--build-location iran`) به نکات زیر به شدت دقت کنید:

1. **ایمیج‌های پایه داکر (Base Images):** هرگز آدرس ایمیج اصلی (مثل `python:3.12-slim`) را به آینه‌هایی مثل `docker.ir` یا `arvancloud` تغییر ندهید. زیرساخت لیارا به طور خودکار کشِ اختصاصی برای داکرهاب دارد و ایمیج‌های استاندارد بدون مشکل دانلود می‌شوند.
2. **دسترسی به سایت (ارور Timeout):** وقتی سایت روی شبکه داخلی ایران دپلوی می‌شود، فقط برای کاربرانی که داخل ایران هستند (بدون فیلترشکن) باز می‌شود. دسترسی از شبکه بین‌الملل خطای Timeout می‌دهد و این به معنای خرابی سایت نیست.
3. **پکیج‌های پایتون (PyPI):** برای جلوگیری از خطای `No route to host` در دانلود پکیج‌ها، حتماً از آینه رسمی لیارا در `Dockerfile` استفاده کنید:
   `ENV PIP_INDEX_URL=https://package-mirror.liara.ir/repository/pypi/simple`
4. **تایم‌اوت هوش مصنوعی لیارا:** مدل‌های هوش مصنوعی لیارا گاهی در پاسخ‌دهی کُند هستند. در فایل‌های پایتون (مثل `ai.py`) حتماً `timeout` کتابخانه `httpx` را روی **۹۰ ثانیه** یا بیشتر تنظیم کنید تا ارور `ReadTimeout` رخ ندهد.
5. **لوکیشن آلمان ممنوع:** اگر برنامه روی ایران ساخته شده است، از سوئیچ کردن به لوکیشن آلمان (`--build-location germany`) خودداری کنید، زیرا بیلد بلافاصله `canceled` می‌شود. فقط روی همان ایران پیش بروید.
