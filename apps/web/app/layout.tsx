import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth/AuthContext";

export const metadata: Metadata = {
  title: "Law Analytics Platform",
  description: "AI-powered legal analytics and market intelligence platform",
  icons: {
    icon: [
      { url: '/favicon.ico' },
      { url: '/icon.png', type: 'image/png' },
    ],
    apple: '/apple-icon.png',
  },
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="ko" className="h-screen overflow-hidden">
      <head>
        <link
          rel="preconnect"
          href="https://cdn.platform.openai.com"
          crossOrigin="anonymous"
        />
        <link rel="dns-prefetch" href="https://cdn.platform.openai.com" />
        <link
          rel="preconnect"
          href="https://api.openai.com"
          crossOrigin="anonymous"
        />
      </head>
      <body className="antialiased h-screen overflow-hidden">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
