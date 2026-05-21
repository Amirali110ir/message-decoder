# استقرار روی Liara

## مسیر پیشنهادی کم‌هزینه: یک app واحد

برای شروع، فقط یک app لازم است که هم FastAPI را اجرا می‌کند و هم خروجی static وب را از همان backend سرو می‌کند.

App پیشنهادی:

- Name: `message-decoder`
- Platform: Docker
- Port: `8000`
- Plan: `small-g2`
- Feature bundle: Bronze
- Network: `message-decoder-net`

Deploy:

```bash
liara deploy \
  --app message-decoder \
  --path . \
  --dockerfile Dockerfile \
  --port 8000 \
  --build-arg NEXT_PUBLIC_API_URL= \
  --message "deploy single app"
```

در این حالت `NEXT_PUBLIC_API_URL` خالی می‌ماند تا frontend همان origin سرور را صدا بزند.

## مسیر دو app جدا

اگر بعداً بخواهیم frontend و backend جدا scale شوند، پروژه به دو app جدا روی Liara نیاز دارد:

1. `message-decoder-api`
2. `message-decoder-web`

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
  --app message-decoder-api \
  --path apps/api \
  --dockerfile Dockerfile \
  --port 8000 \
  --message "deploy api"
```

برای SQLite پایدار باید یک disk روی مسیر `/data` به app API وصل شود. برای production بهتر است PostgreSQL جایگزین SQLite شود.

## 6. Deploy Web

```bash
liara deploy \
  --app message-decoder-web \
  --path . \
  --dockerfile apps/web/Dockerfile \
  --port 3000 \
  --build-arg NEXT_PUBLIC_API_URL=https://YOUR_API_DOMAIN \
  --message "deploy web"
```

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
