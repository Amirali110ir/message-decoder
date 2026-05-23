import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Message Decoder | تحلیل پیام مبهم و ساخت پاسخ کم‌تنش",
  description: "پیام‌های سرد، مبهم یا احساسی را قبل از جواب دادن تحلیل کنید؛ برداشت محتمل، ریسک سوءتفاهم و مسیر پاسخ کم‌تنش‌تر را ببینید."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
