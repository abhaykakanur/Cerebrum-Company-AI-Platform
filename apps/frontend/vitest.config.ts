import path from "node:path";

import { defineConfig } from "vitest/config";

export default defineConfig({
  resolve: {
    // Mirrors tsconfig.json's "@/*" path mapping — Vitest runs on Vite,
    // which doesn't read tsconfig paths on its own.
    alias: {
      "@": path.resolve(__dirname, "."),
    },
  },
  test: {
    environment: "jsdom",
    include: ["tests/unit/**/*.test.{ts,tsx}"],
    globals: true,
  },
});
