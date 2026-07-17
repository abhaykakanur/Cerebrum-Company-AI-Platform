# Networking Overview

## The `cerebrum-network` Bridge

Every service in `infrastructure/docker/docker-compose.yml` joins a single
dedicated bridge network named `cerebrum-network`. This gives:

- **Internal DNS resolution** — any container on the network can reach
  another by its service name (e.g., `postgres`, `neo4j`, `minio`) rather
  than an IP address, which is why the `minio-init` job connects to
  `http://minio:9000`, not a hardcoded IP.
- **Service isolation** — a service is reachable from the host machine
  only through its explicit `ports:` mapping (see `port-allocation.md`);
  nothing is exposed that isn't deliberately mapped.
- **A single, predictable network to reason about** — no per-service
  custom networks, no accidental cross-project bridge sharing.

## Two Address Spaces

There are two distinct ways to reach a service, and mixing them up is the
single most common local-development networking mistake:

| From | Address | Example |
|---|---|---|
| **Another container** on `cerebrum-network` | Service name, internal port | `http://minio:9000` |
| **The host machine** (your terminal, a locally-run backend process, a browser) | `localhost`, mapped host port | `http://localhost:9000` |

A future backend process running natively on your host (not yet
containerized at this milestone) connects via `localhost:<mapped-port>`.
Once the backend itself is containerized in a later phase and joins
`cerebrum-network`, it will switch to using service names, matching the
pattern `minio-init` already demonstrates.

## Future Scalability Readiness

This single-bridge-network design is intentionally simple for local
development, consistent with
`docs/architecture/specification/95_DevOps_Architecture.md`'s Docker
Compose Decision Rationale. It is not the production network topology —
production deployment (Kubernetes-based, per
`docs/architecture/specification/96_Deployment_Strategy.md`) uses
Kubernetes-native service discovery and network policies instead, a
distinct, later concern this local infrastructure does not need to
anticipate in detail.
