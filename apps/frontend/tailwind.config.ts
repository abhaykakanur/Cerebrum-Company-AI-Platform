import type { Config } from "tailwindcss";
import animate from "tailwindcss-animate";

// Design tokens (color, typography, spacing, radius, shadow, motion,
// elevation, z-index, icon-size scales) are centralized here per the
// Design-System-First mandate —
// docs/architecture/specification/85_Frontend_Architecture.md and
// docs/architecture/specification/86_Enterprise_Design_System.md. No
// page or component may hardcode a raw color/spacing/radius value —
// every visual value traces back to a token defined in this file (or
// the CSS custom properties in app/globals.css that back the color
// tokens, for dark/light theme swapping).

const config: Config = {
  darkMode: ["class"], // Dark Theme First — 86_Enterprise_Design_System.md's Visual Language
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "./layouts/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      // --- Color: semantic tokens only, never raw values in components ---
      colors: {
        border: "hsl(var(--border) / <alpha-value>)",
        "border-strong": "hsl(var(--border-strong) / <alpha-value>)",
        input: "hsl(var(--input) / <alpha-value>)",
        ring: "hsl(var(--ring) / <alpha-value>)",
        background: "hsl(var(--background) / <alpha-value>)",
        "background-elevated":
          "hsl(var(--background-elevated) / <alpha-value>)",
        "background-overlay": "hsl(var(--background-overlay) / <alpha-value>)",
        foreground: "hsl(var(--foreground) / <alpha-value>)",
        "foreground-muted": "hsl(var(--foreground-muted) / <alpha-value>)",
        primary: {
          DEFAULT: "hsl(var(--primary) / <alpha-value>)",
          foreground: "hsl(var(--primary-foreground) / <alpha-value>)",
        },
        secondary: {
          DEFAULT: "hsl(var(--secondary) / <alpha-value>)",
          foreground: "hsl(var(--secondary-foreground) / <alpha-value>)",
        },
        success: {
          DEFAULT: "hsl(var(--success) / <alpha-value>)",
          foreground: "hsl(var(--success-foreground) / <alpha-value>)",
        },
        warning: {
          DEFAULT: "hsl(var(--warning) / <alpha-value>)",
          foreground: "hsl(var(--warning-foreground) / <alpha-value>)",
        },
        danger: {
          DEFAULT: "hsl(var(--danger) / <alpha-value>)",
          foreground: "hsl(var(--danger-foreground) / <alpha-value>)",
        },
        info: {
          DEFAULT: "hsl(var(--info) / <alpha-value>)",
          foreground: "hsl(var(--info-foreground) / <alpha-value>)",
        },
        card: {
          DEFAULT: "hsl(var(--card) / <alpha-value>)",
          foreground: "hsl(var(--card-foreground) / <alpha-value>)",
        },
        popover: {
          DEFAULT: "hsl(var(--popover) / <alpha-value>)",
          foreground: "hsl(var(--popover-foreground) / <alpha-value>)",
        },
        muted: {
          DEFAULT: "hsl(var(--muted) / <alpha-value>)",
          foreground: "hsl(var(--muted-foreground) / <alpha-value>)",
        },
        accent: {
          DEFAULT: "hsl(var(--accent) / <alpha-value>)",
          foreground: "hsl(var(--accent-foreground) / <alpha-value>)",
        },
      },

      // --- Typography: Inter (primary) + JetBrains Mono (code) ---
      fontFamily: {
        sans: ["var(--font-inter)", "ui-sans-serif", "system-ui", "sans-serif"],
        mono: [
          "var(--font-jetbrains-mono)",
          "ui-monospace",
          "SFMono-Regular",
          "monospace",
        ],
      },
      // Seven-level hierarchy: Display, H1, H2, H3, Body, Caption, Code.
      fontSize: {
        display: [
          "3.5rem",
          { lineHeight: "1.1", letterSpacing: "-0.02em", fontWeight: "700" },
        ],
        h1: [
          "2.5rem",
          { lineHeight: "1.15", letterSpacing: "-0.015em", fontWeight: "700" },
        ],
        h2: [
          "1.875rem",
          { lineHeight: "1.2", letterSpacing: "-0.01em", fontWeight: "600" },
        ],
        h3: [
          "1.5rem",
          { lineHeight: "1.25", letterSpacing: "-0.005em", fontWeight: "600" },
        ],
        body: ["0.9375rem", { lineHeight: "1.6", fontWeight: "400" }],
        caption: ["0.8125rem", { lineHeight: "1.5", fontWeight: "400" }],
        code: ["0.8125rem", { lineHeight: "1.6", fontWeight: "400" }],
      },

      // --- Spacing: 8-point grid (Tailwind's default 4px scale already
      // covers every 8px multiple at even steps; `18`/`22` fill the two
      // gaps the default scale skips) ---
      spacing: {
        18: "4.5rem",
        22: "5.5rem",
      },

      // --- Border radius: named scale, 12-20px range ---
      borderRadius: {
        sm: "0.5rem",
        DEFAULT: "0.75rem",
        md: "0.875rem",
        lg: "1rem",
        xl: "1.25rem",
      },

      // --- Shadows: layered, low-noise (per 86's "avoid excessive
      // shadows" exclusion — these stay soft/subtle) ---
      boxShadow: {
        xs: "0 1px 2px 0 rgb(0 0 0 / 0.3)",
        sm: "0 2px 6px -1px rgb(0 0 0 / 0.3), 0 1px 3px -1px rgb(0 0 0 / 0.2)",
        DEFAULT:
          "0 4px 14px -2px rgb(0 0 0 / 0.35), 0 2px 6px -2px rgb(0 0 0 / 0.25)",
        md: "0 8px 24px -4px rgb(0 0 0 / 0.4), 0 4px 10px -4px rgb(0 0 0 / 0.3)",
        lg: "0 16px 40px -8px rgb(0 0 0 / 0.45)",
        glow: "0 0 0 1px hsl(var(--primary) / 0.4), 0 0 24px -4px hsl(var(--primary) / 0.5)",
      },

      // --- Blur: Premium Glassmorphism ---
      backdropBlur: {
        xs: "4px",
      },

      // --- Motion: <250ms per Microinteraction rule ---
      transitionDuration: {
        fast: "120ms",
        DEFAULT: "180ms",
        slow: "250ms",
      },
      transitionTimingFunction: {
        DEFAULT: "cubic-bezier(0.4, 0, 0.2, 1)",
        emphasized: "cubic-bezier(0.2, 0, 0, 1)",
      },
      keyframes: {
        "fade-in": { from: { opacity: "0" }, to: { opacity: "1" } },
        "slide-up": {
          from: { opacity: "0", transform: "translateY(8px)" },
          to: { opacity: "1", transform: "translateY(0)" },
        },
        shimmer: {
          "0%": { backgroundPosition: "-200% 0" },
          "100%": { backgroundPosition: "200% 0" },
        },
        "slide-in-from-right": {
          from: { transform: "translateX(100%)" },
          to: { transform: "translateX(0)" },
        },
        "slide-out-to-right": {
          from: { transform: "translateX(0)" },
          to: { transform: "translateX(100%)" },
        },
      },
      animation: {
        "fade-in": "fade-in 180ms ease-out",
        "slide-up": "slide-up 180ms cubic-bezier(0.2, 0, 0, 1)",
        shimmer: "shimmer 2s linear infinite",
        "slide-in-from-right":
          "slide-in-from-right 220ms cubic-bezier(0.2, 0, 0, 1)",
        "slide-out-to-right":
          "slide-out-to-right 180ms cubic-bezier(0.4, 0, 1, 1)",
      },

      // --- Elevation: named layer scale, paired with z-index below ---
      // (elevation 0 = flush content, 1 = card, 2 = sticky nav/dropdown,
      // 3 = drawer, 4 = dialog/modal, 5 = toast — see z-index tokens)

      // --- Z-index: single centralized stacking order — no component
      // defines an ad hoc z-index (86_Enterprise_Design_System.md) ---
      zIndex: {
        base: "0",
        raised: "10",
        sticky: "20",
        overlay: "30",
        drawer: "40",
        dialog: "50",
        popover: "60",
        toast: "70",
        tooltip: "80",
      },

      // --- Icon sizes: named scale ---
      width: {
        "icon-xs": "0.875rem",
        "icon-sm": "1rem",
        "icon-md": "1.25rem",
        "icon-lg": "1.5rem",
        "icon-xl": "2rem",
      },
      height: {
        "icon-xs": "0.875rem",
        "icon-sm": "1rem",
        "icon-md": "1.25rem",
        "icon-lg": "1.5rem",
        "icon-xl": "2rem",
      },
    },
  },
  plugins: [animate],
};

export default config;
