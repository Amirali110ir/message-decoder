# TODO - Message Decoder

این فایل منبع عملیاتی ادامه کار است و از `development_plan.md` و `specification2.md` ساخته شده است.

## Legend

- `[x]` انجام شده و تست/چک پایه دارد.
- `[~]` نیمه انجام شده یا نیازمند پولیش/اتصال کامل است.
- `[ ]` انجام نشده.

## MVP پایه

- [x] ساخت monorepo با `apps/web` و `apps/api`.
- [x] راه‌اندازی FastAPI، Next.js، RTL فارسی و static export.
- [x] مدل‌های اصلی SQLite برای users, messages, decodes, payments, feedback, referrals, prompt_versions و analytics_events.
- [x] landing فارسی و صفحه decoder.
- [x] فرم پیام با relationship type، user goal و optional context.
- [x] `POST /decode/free` با safety check، privacy warning، lens classification و خروجی رایگان.
- [x] نمایش free decode، ریسک، جهت پاسخ، confidence، برداشت جایگزین و CTA پولی.
- [x] `POST /decode/paid` با credit و پاسخ‌های قابل کپی.
- [x] copy event و feedback.
- [x] OTP mock، session token و `GET /user/credits`.
- [x] payment create/verify با adapter sandbox-shaped زرین‌پال.
- [x] AI pipeline با JSON validation، prompt/model version و fallback rule-based.
- [x] safety mode و manipulation redirect.
- [x] analytics events پایه.
- [x] پرداخت زرین‌پال واقعی: sandbox، request/verify production، callback و authority/ref_id اضافه شد.

## انجام شده در دور اخیر

- [x] `lens_mix` به خروجی free decode اضافه شد.
- [x] `tone_stress` به خروجی free decode اضافه شد.
- [x] Interaction Radar / donut chart در صفحه decoder اضافه شد.
- [x] Tone Thermometer در صفحه decoder اضافه شد.
- [x] Ghost Mode در schema، backend و UI اضافه شد.
- [x] Ghost Mode دیگر row در `messages` و `decodes` ذخیره نمی‌کند.
- [x] Ghost Mode cache ذخیره AI را برای free decode دور می‌زند.
- [x] contacts backend و API client وصل شدند.
- [x] UI حداقلی برای ساخت و انتخاب مخاطب بعد از login اضافه شد.
- [x] `profile_summary` مخاطب به context پرامپت free/paid اضافه شد.
- [x] تست‌های backend برای lens mix، ghost mode و contact interaction اضافه شد.
- [x] frontend برای پاسخ‌های قدیمی/کش‌شده بدون `lens_mix` یا `tone_stress` fallback دارد.

## کارهای باقی‌مانده فوری

- [x] QA تصویری واقعی با browser/screenshot روی desktop و mobile برای decoder جدید.
- [x] اجرای smoke flow از مسیر API: login، ساخت contact، free decode، paid decode، copy، feedback.
- [x] اجرای flow دستی کامل از داخل UI مرورگر: login، ساخت contact، free decode، paid decode، copy، feedback.
- [x] UX polish برای Contact Memory:
  - [x] نمایش selected contact profile summary بعد از انتخاب.
  - [x] امکان edit/delete مخاطب از UI.
  - [x] empty/login state بهتر برای مخاطبین.
- [x] Ghost Mode polish:
  - [x] copy event و feedback برای ghost decode یا غیرفعال شوند یا رفتار privacy-safe مشخص بگیرند.
  - [x] متن UI دقیق‌تر کند که paid decode از ghost result ممکن نیست.
  - [x] تست API برای اینکه paid decode روی ghost decode `404` یا پیام مناسب می‌دهد.
- [x] Admin:
  - [x] endpoint برای لیست decodeهای anonymized.
  - [x] فیلتر با relationship type، lens، safety label و prompt version.
  - [x] UI جدول decodeهای anonymized در `/admin`.
- [x] Payment:
  - [x] adapter زرین‌پال واقعی با callback و authority/ref_id.
  - [x] تست verify موفق/ناموفق production-shaped.
- [x] Persistence/History:
  - [x] history اختیاری کاربر.
  - [x] امکان حذف history و داده‌های ذخیره‌شده کاربر.

## کارهای بعدی از `specification2.md`

- [x] Relationship Thermometer بر اساس تاریخچه مخاطب.
- [x] Reaction Simulator کنار هر reply option.
- [x] `/feedback/selected-reply` برای یادگیری سبک پاسخ انتخاب‌شده.
- [x] به‌روزرسانی profile_summary مخاطب بر اساس feedback و پاسخ انتخابی.
- [x] Playbook Hub برای سناریوهای آماده.
- [x] Telegram Assistant Bot با backend مشترک (Cloudflare Worker کامل + FastAPI webhook fallback).
- [ ] Chrome Extension برای Gmail/LinkedIn/Slack-like surfaces.
- [ ] Share card بدون متن حساس.
- [x] Referral credit (وب: verify_otp +۵ به معرف؛ تلگرام: deep-link `start=ref_` و `/referral` در هر دو بات).
- [x] Tone edit buttons برای پاسخ‌ها (`POST /decode/tone-edit` + دکمه‌های لحن کنار هر پاسخ).
- [x] Before-send checker (`POST /decode/before-send` + کارت بررسی قبل از ارسال در decoder).
- [ ] Screenshot/OCR بعد از تثبیت MVP.
- [ ] Mobile custom keyboard در فاز نهایی.

## تست‌های لازم قبل از هر ship

- [x] `python3 -m pytest` در `apps/api`.
- [x] `npx tsc --noEmit --incremental false` در `apps/web`.
- [x] `npm run build` در `apps/web`.
- [ ] smoke test روی `/decoder/`.
- [ ] اگر UI تغییر کرده: screenshot desktop/mobile و بررسی overlap.

## اولویت پیشنهادی بعدی

1. Share card بدون متن حساس (تنها آیتم retention باقی‌مانده از فاز فعلی).
2. Chrome Extension برای surfaceهای Gmail/LinkedIn/Slack.
3. Screenshot/OCR و keyboard بعد از تثبیت کانال‌های اصلی.
4. polish تصویری نهایی بعد از انتخاب scope بعدی.
