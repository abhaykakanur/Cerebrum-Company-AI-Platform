# Neo4j Configuration

At this milestone, Neo4j is configured through environment variables in
`docker-compose.yml`: authentication credentials, the APOC plugin
(provisioned proactively for future graph-extraction and traversal
features — see
`docs/architecture/specification/35_Domain_Architecture.md`'s Knowledge
Graph Domain — but unused by any code yet), and heap memory sizing.

**This directory is reserved** for a future `neo4j.conf` override once a
concrete tuning need is identified — for example, once
`docs/architecture/specification/46_Multi_Tenancy.md`'s query-layer tenant
isolation enforcement is implemented and its performance characteristics
are measured (see Open Question 62 in
`docs/architecture/specification/49_Open_Questions.md`).

No graph data, constraints, or indexes are created at this milestone.
