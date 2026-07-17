# @cerebrum/tsconfig

Shared base `tsconfig.json` files for every TypeScript package and app in
the workspace, so TypeScript Strict Mode
(`docs/architecture/specification/99_Coding_Standards.md`) is enforced
identically everywhere rather than configured per-package.

## Public Interfaces

- `base.json` — the strict foundation every other config extends.
- `nextjs.json` — for Next.js apps (extends `base.json`).
- `library.json` — for buildable library packages (extends `base.json`).

## Usage

```json
{
  "extends": "@cerebrum/tsconfig/library.json"
}
```

## Dependencies

None — pure configuration.

## Limitations

No package may add a tsconfig that relaxes `strict: true` or any other
setting in `base.json` without an ADR
(`docs/architecture/specification/09_Governance.md`) justifying the
exception.
