import type { Metadata } from "next";
import "./styles.css";

export const metadata: Metadata = {
  title: "Message Decoder by NeuroLens",
  description: "قبل از جواب دادن، پیامش را رمزگشایی کن."
};

export default function RootLayout({ children }: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="fa" dir="rtl">
      <body>{children}</body>
    </html>
  );
}

