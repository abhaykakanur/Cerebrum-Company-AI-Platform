/**
 * Cerebrum base ESLint configuration.
 *
 * Shared across every TypeScript package/app so linting behaves
 * identically everywhere — see
 * docs/architecture/specification/99_Coding_Standards.md's "no lint
 * warnings allowed in production" binding rule. `next.js` and
 * `library.js` in this package extend this base with environment-specific
 * additions (e.g., Next.js's own recommended rules).
 */
module.exports = {
  root: true,
  extends: ["eslint:recommended", "plugin:@typescript-eslint/recommended", "prettier"],
  parser: "@typescript-eslint/parser",
  plugins: ["@typescript-eslint"],
  env: {
    es2022: true,
    node: true,
  },
  parserOptions: {
    ecmaVersion: "latest",
    sourceType: "module",
  },
  rules: {
    // No magic numbers, meaningful names, small functions, explicit error
    // handling — docs/architecture/specification/99_Coding_Standards.md's
    // General Rules, enforced here where ESLint can check them mechanically.
    "@typescript-eslint/no-unused-vars": ["error", { argsIgnorePattern: "^_" }],
    "@typescript-eslint/no-explicit-any": "error",
    "no-console": ["warn", { allow: ["warn", "error"] }],
  },
  ignorePatterns: ["dist", ".next", "node_modules", "coverage"],
};
