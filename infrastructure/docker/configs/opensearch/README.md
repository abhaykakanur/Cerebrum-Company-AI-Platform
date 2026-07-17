# OpenSearch Configuration

At this milestone, OpenSearch runs in single-node development mode with
the security plugin disabled, configured entirely through environment
variables in `docker-compose.yml`. This is explicitly a **local-development-only**
configuration — see the warning comment in that file and
`docs/deployment/troubleshooting.md`.

**This directory is reserved** for a future `opensearch.yml` override once:

1. OpenSearch's formal tenant-isolation and data-ownership treatment is
   resolved (`docs/architecture/specification/49_Open_Questions.md`,
   Open Question 55 — OpenSearch was not among the five datastores given
   full Part 4 data-architecture treatment), and
2. Staging/Production security-plugin configuration (TLS, role-based
   access) is designed, which is explicitly out of scope for local
   development infrastructure.

No indexes, mappings, or index templates are created at this milestone —
see `infrastructure/docker/init/opensearch/` for the (currently empty)
initialization hook reserved for that future work.
