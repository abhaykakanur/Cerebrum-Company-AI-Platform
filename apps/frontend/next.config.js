/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@cerebrum/shared-types", "@cerebrum/shared-utils"],

  // Standalone output — the Docker runtime image (apps/frontend/Dockerfile)
  // copies only `.next/standalone` + `.next/static`, not the full
  // node_modules tree, matching the backend Dockerfile's "shipped image
  // never contains build tooling" convention.
  output: "standalone",

  // NEXT_PUBLIC_API_BASE_URL is read at runtime — see .env.example and
  // docs/deployment/environment-variables.md. No API rewrites/proxying are
  // configured: the browser calls the backend's `/api/v1` origin directly,
  // per docs/architecture/specification/85_Frontend_Architecture.md's
  // Thin Frontend boundary (the frontend never proxies or mediates API
  // traffic).
};

module.exports = nextConfig;
