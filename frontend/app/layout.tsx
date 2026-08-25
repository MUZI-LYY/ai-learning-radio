import type { Metadata, Viewport } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "AI 学习电台",
  description: "把学习资料转换成可收听、可复习的中文节目",
  applicationName: "AI 学习电台",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "学习电台",
  },
};

export const viewport: Viewport = {
  width: "device-width",
  initialScale: 1,
  maximumScale: 1,
  themeColor: "#f5f6f1",
};

export default function RootLayout({
  children,
}: Readonly<{ children: React.ReactNode }>) {
  return (
    <html lang="zh-CN">
      <body>{children}</body>
    </html>
  );
}
