import "./globals.css";
import type { Metadata } from "next";

export const metadata: Metadata = {
  title: "법률 에이전트 실험실",
  description: "OpenAI 호환 엔드포인트와 연동되는 법률 도구 타임라인 UI"
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <html lang="ko" suppressHydrationWarning>
      <body className="antialiased">
        {children}
      </body>
    </html>
  );
}
