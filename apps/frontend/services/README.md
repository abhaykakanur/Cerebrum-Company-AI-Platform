# services/

Frontend-side service modules wrapping `lib/`'s API client into
feature-consumable functions. Per the Thin Frontend principle
(`docs/architecture/specification/85_Frontend_Architecture.md`), this
layer contains request orchestration only — never business logic, which
belongs exclusively server-side. Empty at Repository Foundation.
