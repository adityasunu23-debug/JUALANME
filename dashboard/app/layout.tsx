import type { Metadata } from "next";

import { ToastProvider } from "@/components/toast";
import { AuthProvider } from "@/lib/auth";

import "./globals.css";

export const metadata: Metadata = {
  title: "Telegram Store · Admin",
  description: "Crypto store dashboard for orders, stock and customer support.",
  robots: { index: false, follow: false },
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="dark">
      <body>
        <AuthProvider>
          <ToastProvider>{children}</ToastProvider>
        </AuthProvider>
      </body>
    </html>
  );
}
