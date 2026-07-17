import type { Config } from "tailwindcss";

// Design tokens (color, typography, spacing, radius, shadow, motion scales)
// are centralized here per the Design-System-First mandate —
// docs/architecture/specification/85_Frontend_Architecture.md and
// docs/architecture/specification/86_Enterprise_Design_System.md.
//
// No token VALUES are populated yet at this milestone (Repository
// Foundation only) — the Enterprise Design System's actual palette,
// scale, and component tokens are Phase 1 Prompt 3+ scope. This file
// establishes the extension point so no page or component ever needs to
// hardcode a design value, per that document's binding rule.

const config: Config = {
  darkMode: "class", // Dark Theme First — docs/architecture/specification/86_Enterprise_Design_System.md
  content: [
    "./app/**/*.{ts,tsx}",
    "./components/**/*.{ts,tsx}",
    "./features/**/*.{ts,tsx}",
    "./layouts/**/*.{ts,tsx}",
  ],
  theme: {
    extend: {
      // Reserved for the Design Token categories in
      // docs/architecture/specification/86_Enterprise_Design_System.md:
      // colors, fontFamily, spacing (8-point grid), borderRadius,
      // boxShadow, backdropBlur, opacity, transitionDuration (motion),
      // zIndex. Intentionally empty until the Design System milestone.
    },
  },
  plugins: [],
};

export default config;
