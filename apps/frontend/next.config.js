/** @type {import('next').NextConfig} */
const nextConfig = {
  reactStrictMode: true,
  transpilePackages: ["@cerebrum/shared-types", "@cerebrum/shared-utils"],

  // NEXT_PUBLIC_API_BASE_URL is read at runtime — see .env.example and
  // docs/deployment/environment-variables.md. No API rewrites/proxying are
  // configured yet since no backend API endpoints exist at this milestone
  // (docs/architecture/specification/80_API_Architecture.md onward, not
  // implemented until a later Phase 1 prompt).
};

module.exports = nextConfig;
