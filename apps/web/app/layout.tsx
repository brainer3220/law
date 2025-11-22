import type { Metadata } from "next";
import "./globals.css";
import { AuthProvider } from "@/lib/auth/AuthContext";
import ChatKitScript from "@/components/ChatKitScript";

export const metadata: Metadata = {
  title: "AgentKit demo",
  description: "Demo of ChatKit with hosted workflow",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="h-screen overflow-hidden">
      <head>
        <ChatKitScript />
      </head>
      <body className="antialiased h-screen overflow-hidden">
        <AuthProvider>{children}</AuthProvider>
      </body>
    </html>
  );
}
