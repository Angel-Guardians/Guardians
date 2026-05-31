import type { Metadata } from "next";
import { Geist, Geist_Mono } from "next/font/google";

import { SessionGate } from "@/components/session-gate";
import { ThemeProvider } from "@/components/theme-provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Guardian",
  description: "Home Emergency AI Companion - always-on, fully local",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html
      lang="en"
      suppressHydrationWarning
      className={`${geistSans.variable} ${geistMono.variable} h-full antialiased`}
    >
      <body className="min-h-full bg-background">
        <ThemeProvider>
          <SessionGate>{children}</SessionGate>
        </ThemeProvider>
      </body>
    </html>
  );
}
