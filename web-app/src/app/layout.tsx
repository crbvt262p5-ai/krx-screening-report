import type { Metadata } from "next";
import "./globals.css";

export const metadata: Metadata = {
  title: "멍칼로리 계산기",
  description: "강아지별 사료와 간식 칼로리를 관리하는 모바일 우선 웹앱",
  applicationName: "멍칼로리 계산기",
  appleWebApp: {
    capable: true,
    statusBarStyle: "default",
    title: "멍칼로리 계산기",
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
