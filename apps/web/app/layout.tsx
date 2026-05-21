import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Message Decoder by NeuroLens",
  description: "پیام‌های مبهم را با تحلیل الهام‌گرفته از علوم اعصاب و روان‌شناسی رفتاری واضح‌تر بفهمید و امن‌تر پاسخ دهید."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}
