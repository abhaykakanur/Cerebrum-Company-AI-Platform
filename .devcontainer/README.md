# .devcontainer/

Ready-to-use development environment for
[GitHub Codespaces](https://github.com/features/codespaces) and
[VS Code Dev Containers](https://code.visualstudio.com/docs/devcontainers/containers).

## What It Provides

- Python 3.12 + [uv](https://docs.astral.sh/uv/)
- Node.js 20 + pnpm 9
- Docker CLI (via the `docker-outside-of-docker` feature), so
  `scripts/start.sh` works identically inside the devcontainer, forwarding
  to the host's Docker daemon
- All ports from `docs/deployment/port-allocation.md` pre-forwarded
- The same VS Code extensions and settings every local contributor uses
  (`.vscode/`)

## Usage

**GitHub Codespaces:** Click "Code" → "Create codespace on main" on
GitHub. Setup runs automatically via `postCreateCommand`
(`scripts/setup.sh`).

**VS Code locally:** Install the "Dev Containers" extension, then
"Reopen in Container" from the command palette.

## What Happens on Create

`scripts/setup.sh` runs automatically — installs dependencies for both
workspaces, provisions `.env`, and starts local infrastructure. See
`docs/development/getting-started.md` for what to expect afterward.
