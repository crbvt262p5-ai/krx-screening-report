import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "내 투자자산 | 포트폴리오 대시보드",
  description: "보유자산, 수익률, 비중과 투자 인사이트를 한눈에 확인하는 포트폴리오 대시보드",
  applicationName: "내 투자자산",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "내 투자자산",
  },
  formatDetection: {
    telephone: false,
  },
  manifest: "/manifest.webmanifest",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-full antialiased">
      <body className="min-h-full flex flex-col">{children}</body>
    </html>
  );
}
