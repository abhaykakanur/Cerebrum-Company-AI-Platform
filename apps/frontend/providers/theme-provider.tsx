"use client";

import * as React from "react";
import { ThemeProvider as NextThemesProvider } from "next-themes";
import type { ThemeProviderProps } from "next-themes/dist/types";

// Dark Theme First — docs/architecture/specification/86_Enterprise_Design_System.md.
// `next-themes` toggles a "dark"/"light" class on <html>; app/globals.css
// defines the dark palette on both :root (pre-hydration default, avoids
// a flash of incorrect theme) and .dark (post-hydration, once
// next-themes has committed a choice), with .light overriding it.
export function ThemeProvider({ children, ...props }: ThemeProviderProps) {
  return (
    <NextThemesProvider
      attribute="class"
      defaultTheme="dark"
      enableSystem={false}
      {...props}
    >
      {children}
    </NextThemesProvider>
  );
}
