# @cerebrum/shared-types

TypeScript types shared between the frontend and any other TypeScript
consumer — the frontend-side mirror of backend DTOs.

## Public Interfaces

`src/index.ts` — currently empty; re-exports future domain type modules
as they're added.

## Dependencies

None at runtime — types only, erased at compile time.

## Usage

```ts
import type { /* future export */ } from "@cerebrum/shared-types";
```

Consumed directly from TypeScript source (no build step) via each
consumer's bundler — e.g., `apps/frontend/next.config.js`'s
`transpilePackages`. A compiled-`dist` build step can be added later if a
non-bundler consumer needs it; not necessary yet.

## Limitations

Empty at Repository Foundation. No API contract exists yet to describe.
