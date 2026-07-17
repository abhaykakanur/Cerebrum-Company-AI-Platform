# Cerebrum Backend

The Modular Monolith backend implementing all 30 CES functional domains.
See `docs/architecture/specification/30_System_Architecture.md` for the
full architecture this package realizes.

## Architecture Overview

This package follows Clean/Hexagonal Architecture
(`docs/architecture/specification/34_Architecture_Principles.md`): each
top-level directory under `src/cerebrum/` is one layer, with dependencies
pointing strictly inward. See `docs/architecture/dependency-rules.md` for
the enforced rule set and `docs/architecture/layer-responsibilities.md`
for what belongs in each layer.

## Public Interfaces

None yet — no API endpoints exist at this milestone (Repository
Foundation, Phase 1 Prompt 1). See
`docs/architecture/specification/80_API_Architecture.md` for the eventual
API Domain surface.

## Dependencies

- Python 3.12+
- FastAPI, Pydantic (see `pyproject.toml`)
- Managed via [uv](https://docs.astral.sh/uv/) as a workspace member of
  the repository root's `pyproject.toml`

## Configuration

See `.env.example` at the repository root and
`docs/architecture/specification/37_Configuration_Strategy.md`.

## Usage

```bash
# From the repository root:
uv sync
uv run pytest apps/backend/tests
```

No application entrypoint exists yet — this package currently installs
and imports cleanly but exposes no runnable server. See
`docs/architecture/specification/110_Implementation_Roadmap.md` for when
that changes (Phase 2, Identity Platform).

## Limitations

- No database models, migrations, or API endpoints (by design — see the
  Repository Foundation milestone's explicit scope).
- No authentication or authorization implementation.
- Every subpackage under `src/cerebrum/` currently contains only an
  `__init__.py` documenting its intended responsibility.
