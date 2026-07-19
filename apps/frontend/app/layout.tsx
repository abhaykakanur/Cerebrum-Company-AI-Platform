import type { Metadata, Viewport } from "next";
import { JetBrains_Mono, Inter } from "next/font/google";

import { AppProviders } from "@/providers/app-providers";

import "./globals.css";

// Typography tokens — Inter (primary) + JetBrains Mono (code), per
// docs/architecture/specification/86_Enterprise_Design_System.md.
// Exposed as CSS variables consumed by tailwind.config.ts's
// `fontFamily` token so no component ever references a font name
// directly.
const inter = Inter({
  subsets: ["latin"],
  variable: "--font-inter",
  display: "swap",
});
const jetbrainsMono = JetBrains_Mono({
  subsets: ["latin"],
  variable: "--font-jetbrains-mono",
  display: "swap",
});

export const metadata: Metadata = {
  title: {
    default: "Cerebrum — Enterprise Knowledge Intelligence",
    template: "%s · Cerebrum",
  },
  description:
    "Cerebrum — the enterprise AI platform that turns your organization's scattered knowledge into a living, evidence-backed intelligence layer.",
};

export const viewport: Viewport = {
  themeColor: [
    { media: "(prefers-color-scheme: dark)", color: "#08090f" },
    { media: "(prefers-color-scheme: light)", color: "#ffffff" },
  ],
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en" className="dark" suppressHydrationWarning>
      <body className={`${inter.variable} ${jetbrainsMono.variable} font-sans`}>
        <AppProviders>{children}</AppProviders>
      </body>
    </html>
  );
}
