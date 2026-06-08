import type { Metadata, Viewport } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Message Decoder | تحلیل پیام مبهم و ساخت پاسخ کم‌تنش",
  description: "پیام‌های سرد، مبهم یا احساسی را قبل از جواب دادن تحلیل کنید؛ برداشت محتمل، ریسک سوءتفاهم و مسیر پاسخ کم‌تنش‌تر را ببینید."
};

// viewportFit:"cover" enables env(safe-area-inset-*) for notch/home-indicator (T12)
export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  viewportFit: "cover"
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl">
      <head>
        <link rel="preconnect" href="https://fonts.googleapis.com" />
        <link rel="preconnect" href="https://fonts.gstatic.com" crossOrigin="anonymous" />
        <link
          href="https://fonts.googleapis.com/css2?family=Vazirmatn:wght@300;400;500;600;700;800&display=swap"
          rel="stylesheet"
        />
      </head>
      <body>{children}</body>
    </html>
  );
}
