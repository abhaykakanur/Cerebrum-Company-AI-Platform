# .github/

Repository community health files, issue/PR templates, and CI workflow
placeholders.

## Contents

| File/Directory | Purpose |
|---|---|
| `ISSUE_TEMPLATE/` | Structured issue forms (bug report, feature request, documentation issue). |
| `DISCUSSION_TEMPLATE/` | Structured discussion forms (Q&A, architecture proposals). |
| `PULL_REQUEST_TEMPLATE.md` | The required PR structure — see `CONTRIBUTING.md`. |
| `CODEOWNERS` | Review-routing rules. **Team handles are placeholders** — see the file's own header note. |
| `labels.yml` | Declarative label taxonomy. Not yet wired to automation — apply manually until it is. |
| `workflows/ci.yml` | A manually-triggered placeholder only. No automated CI runs yet — see `docs/architecture/specification/97_CICD_Architecture.md` for the real, thirteen-stage pipeline this will become. |

## Discussion Categories (Manual Setup Required)

GitHub Discussion categories are a repository setting, not a file this
repository can define — configure them once Discussions is enabled, via
**Settings → Features → Discussions**. Recommended categories, matching
the templates above:

- **Q&A** — general questions (uses `q-a.yml`)
- **Architecture Proposals** — CES changes and Open Question resolution (uses `architecture-proposal.yml`)
- **Announcements** — maintainer-only updates
- **Ideas** — early-stage feature ideas not yet ready for a formal issue

## Placeholder Notice

`CODEOWNERS`'s `@cerebrum/*` team handles and `ISSUE_TEMPLATE/config.yml`'s
contact links use placeholder org/team names — update both once this
repository has a real GitHub remote and real teams assigned, per
`docs/architecture/module-ownership.md`.
