"""Infrastructure layer: adapters implementing domain- and
application-layer port interfaces against real technology (PostgreSQL,
Neo4j, Qdrant, Redis, MinIO, OpenSearch, LLM/embedding providers, secrets
backends).

See docs/architecture/specification/32_Technology_Stack.md and
docs/architecture/specification/42_Database_Responsibilities.md. This is
the only layer permitted to import third-party infrastructure SDKs — see
docs/architecture/dependency-rules.md.
"""
