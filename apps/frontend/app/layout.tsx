import type { Metadata } from "next";
import "./globals.css";

// This is the minimum viable root layout required for Next.js's App Router
// to build and serve a page — it is scaffolding, not a feature. No
// navigation, no providers, no business components. See
// docs/architecture/specification/85_Frontend_Architecture.md's Layout
// System for what this will become in a later implementation phase.

export const metadata: Metadata = {
  title: "Cerebrum",
  description: "Cerebrum — Enterprise Knowledge Intelligence Platform",
};

export default function RootLayout({
  children,
}: Readonly<{
  children: React.ReactNode;
}>) {
  return (
    <html lang="en">
      <body>{children}</body>
    </html>
  );
}
