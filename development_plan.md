# پلن توسعه Message Decoder

## Summary

این فایل برنامه اجرایی ساخت **Message Decoder by NeuroLens** بر اساس `specification.md` است. هدف، ساخت MVP قابل لانچ با وب‌اپ فارسی و backend مشترک است؛ بات تلگرام، share card، referral و history کامل در roadmap بعد از MVP می‌آیند.

استک قفل‌شده:

- Frontend: Next.js
- Backend/API: FastAPI
- Auth: ورود با شماره موبایل و OTP
- Payment: زرین‌پال
- AI: سرویس مدل با خروجی JSON ساختاریافته
- MVP Channel: وب‌اپ
- Roadmap Channel: بات تلگرام با backend مشترک

## Phase 0 — Project Foundation

- ساخت monorepo با دو بخش `apps/web` و `apps/api`.
- تنظیم envها برای API URL، AI provider، OTP provider، Zarinpal، database و Telegram token.
- تعریف RTL فارسی، فونت system، رنگ‌ها و کامپوننت‌های پایه.
- راه‌اندازی SQLite برای توسعه و migration/init ساده برای MVP.
- ساخت مدل‌های اصلی: users, messages, decodes, payments, feedback, referrals, prompt_versions, analytics_events.

## Phase 1 — Core MVP Web App

- Landing فارسی با پیام «قبل از جواب دادن، پیامش را رمزگشایی کن.»
- فرم ورود پیام شامل متن پیام، نوع رابطه، هدف پاسخ و context اختیاری.
- `POST /decode/free` با safety check، privacy warning، lens classification و خروجی رایگان بدون پاسخ کامل.
- نمایش free decode با لنز غالب، معنی ساده لنز، علت انتخاب، ریسک، جهت پاسخ، احتمال خطا و CTA پولی.
- paywall بعد از free decode.
- `POST /decode/paid` با مصرف ۱ کردیت و خروجی پاسخ‌های قابل کپی.
- ثبت copy event برای پاسخ‌های کپی‌شده.

## Phase 2 — Auth, Payment, Credits

- OTP dev/mock برای MVP و interface آماده اتصال provider واقعی.
- ایجاد user بعد از verify موفق.
- `GET /user/credits` برای اعتبار کاربر.
- `POST /payment/create` و `POST /payment/verify` با adapter زرین‌پال.
- بسته‌های اولیه: ۵، ۲۰ و ۵۰ کردیت.
- paid decode فقط برای user authenticated با credit کافی.

## Phase 3 — AI Pipeline & Safety

- ذخیره prompt version پایه از سند مادر.
- خروجی مدل به شکل JSON معتبر برای free و paid.
- safety mode قبل از تحلیل عادی.
- redirect برای درخواست‌های manipulative.
- ذخیره `model_version` و `prompt_version` برای هر decode.

## Phase 4 — Feedback, Privacy, Analytics

- consent قبل از decode: ذخیره نشود، history خودم، ناشناس برای بهبود.
- raw text فقط مطابق consent ذخیره شود.
- anonymized text فقط برای حالت history/anonymized ذخیره شود.
- feedback برای free و paid.
- analytics events برای activation، payment، paid decode، copy و feedback.

## Phase 5 — Basic Admin

- داشبورد admin محافظت‌شده با `ADMIN_TOKEN`.
- نمایش users، free decodes، paid decodes، revenue، conversion و copy rate.
- مشاهده decodeها به شکل anonymized و فیلتر با relationship type، lens، safety label و prompt version.

## Phase 6 — Roadmap After MVP

- Telegram bot با backend مشترک.
- share card بدون متن حساس.
- referral credit.
- tone edit buttons.
- history اختیاری.
- before-send checker.
- screenshot/OCR بعد از تثبیت MVP.

## API Contract

- `POST /auth/request-otp`
- `POST /auth/verify-otp`
- `GET /user/credits`
- `POST /decode/free`
- `POST /decode/paid`
- `POST /payment/create`
- `POST /payment/verify`
- `POST /feedback`
- `POST /copy-event`
- `GET /decode/{id}`
- `GET /admin/metrics`

## Acceptance Criteria

- کاربر فارسی می‌تواند پیام را وارد کند، رابطه و هدف را انتخاب کند، free decode بگیرد، بعد از paywall با credit خروجی paid بسازد و پاسخ را کپی کند.
- محصول هرگز سطح واقعی هورمون، تشخیص روانشناختی، اختلال شخصیت یا نیت قطعی اعلام نمی‌کند.
- safety-risk message خروجی safety-first می‌دهد.
- paid decode با credit صفر blocked می‌شود.
- payment verify ناموفق credit اضافه نمی‌کند.
- copy و feedback ثبت می‌شوند.
- admin metrics بدون نمایش raw sensitive text در دسترس است.

