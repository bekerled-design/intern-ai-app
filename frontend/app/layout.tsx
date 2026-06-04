import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "Стажировка",
  description: "AI-платформа корпоративного обучения",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="ru" className="h-full">
      <body className="min-h-full bg-[#F4F6FB] text-[#111827] antialiased">{children}</body>
    </html>
  );
}
