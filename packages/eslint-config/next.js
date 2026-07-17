/**
 * Cerebrum ESLint configuration for Next.js apps.
 * Extends the shared base (./index.js) with Next.js's own recommended
 * rule set (Core Web Vitals).
 */
module.exports = {
  extends: ["./index.js", "next/core-web-vitals"],
};
