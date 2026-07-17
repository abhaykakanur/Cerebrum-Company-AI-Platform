# @cerebrum/eslint-config

Shared ESLint configuration ensuring "no lint warnings allowed in
production" (`docs/architecture/specification/99_Coding_Standards.md`) is
enforced identically across every TypeScript package/app.

## Public Interfaces

- `@cerebrum/eslint-config` (`index.js`) — the base rule set.
- `@cerebrum/eslint-config/next` (`next.js`) — base + Next.js Core Web Vitals.
- `@cerebrum/eslint-config/library` (`library.js`) — base only, for plain
  TypeScript packages.

## Usage

```json
{
  "extends": ["@cerebrum/eslint-config/next"]
}
```

## Dependencies

`@typescript-eslint/parser`, `@typescript-eslint/eslint-plugin`,
`eslint-config-prettier` (disables ESLint rules that conflict with
Prettier's formatting — the two tools are never allowed to fight over the
same concern).

## Limitations

No package may disable a rule from this shared config inline without a
comment explaining why — silent, undocumented rule suppression is exactly
what `docs/architecture/specification/95_DevOps_Architecture.md`'s "no
quick fixes become permanent architecture" rule exists to prevent.
