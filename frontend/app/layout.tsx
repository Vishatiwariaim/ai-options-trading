import "./globals.css";
import type { Metadata } from "next";
import { AuthProvider } from "@/lib/auth";
import { Nav } from "@/components/Nav";
import { Disclaimer } from "@/components/Disclaimer";

export const metadata: Metadata = {
  title: "AI Options Trading Platform",
  description: "Probabilistic NSE/BSE options signals & paper trading. Not financial advice.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en">
      <body>
        <AuthProvider>
          <Nav />
          <main className="max-w-7xl mx-auto px-4 py-6">{children}</main>
          <Disclaimer />
        </AuthProvider>
      </body>
    </html>
  );
}
