# API Versioning Guide

The API Version Registry — `cerebrum.api.versions.API_VERSION_REGISTRY`
— is the authoritative, in-process list of every API major version this
backend serves. Distinct from `cerebrum.config.api.APISettings`: that
says where `v1` is *mounted* (`api_v1_prefix`); this says what versions
*exist* and their status.

## Discovering Versions

```
GET /api/versions
```

```json
{
  "versions": [
    {"version": "v1", "prefix": "/api/v1", "status": "active", "deprecation_notice": null, "migration_guide_url": null}
  ]
}
```

Sunset versions are omitted — see `cerebrum.api.versions.get_active_versions`.

## Lifecycle

`VersionStatus`: `active` → `deprecated` → `sunset`. Per
[81_API_Standards.md](../specification/81_API_Standards.md)'s
Deprecation Policy — a defined window between deprecation notice and
removal is binding; the exact window length is Deferred to Architecture
(Open Question 36).

To deprecate a version, edit its registry entry in place — never delete
it:

```python
APIVersion(
    version="v1",
    prefix="/api/v1",
    status=VersionStatus.DEPRECATED,
    deprecation_notice="v1 is deprecated as of 2027-01-01; migrate to v2 by 2027-07-01.",
    migration_guide_url="https://docs.cerebrum.example/migration/v1-to-v2",
)
```

Deleting the entry instead would leave `get_version("v1")` unable to
explain to a client why a version it remembers no longer resolves.

## Adding a New Major Version

1. Append a new `APIVersion` entry to `API_VERSION_REGISTRY` (never
   mutate the `v1` entry's `version`/`prefix`).
2. Mount the new version's router the same way `cerebrum.api.v1.router`
   is mounted today, at its own prefix (e.g. `/api/v2`).
3. Write Migration Documentation — the guide a `v1` client reads to
   upgrade — and link it via `migration_guide_url` once `v1` moves to
   `deprecated`.

A minor version increment (backward-compatible additions — new optional
fields, new endpoints) does **not** get a new registry entry; only
breaking changes ship in a new major version, per
[81_API_Standards.md](../specification/81_API_Standards.md)'s API
Versioning section.
