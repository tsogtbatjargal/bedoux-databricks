# Local development

Use Python 3.11 in a project `.venv` managed by uv. The pure-Python generator and
transform tests need no Databricks workspace, Spark install, or model API key.
Databricks supplies Spark and pipeline libraries in its own runtime; do not
install unrelated packages named `dlt` to make pipeline imports work locally.

## Setup

Install [uv](https://docs.astral.sh/uv/getting-started/installation/) if needed.
This repository also pins uv in `mise.toml` for contributors who use mise:

```bash
mise trust
mise install
```

With uv on PATH, run:

```bash
uv sync --locked
uv run --locked python -m pytest -q
```

If mise's shell activation is not enabled, prefix commands with `mise exec --`,
for example `mise exec -- uv sync --locked`. No global tool selection or shell
profile edit is required. uv can download Python 3.11 if it is missing. Packages
are installed in `.venv/`; shared download caches are outside the repository.

`.python-version` selects the local/CI interpreter. `pyproject.toml` declares
dependencies and `uv.lock` pins resolved versions. Keep both dependency files in
Git. The old `requirements-dev.txt` has been replaced, not maintained in parallel.

## Dependencies and separate environments

```bash
uv add --dev PACKAGE_NAME
uv lock --check
uv run --locked python -m pytest -q
```

Review the dependency and lockfile diff together. Use `uv lock --upgrade-package`
with a named package for a deliberate upgrade. Do not run `uv pip install` or
system pip to make an undeclared dependency silently available.

Each clone or Git worktree gets its own `.venv`. Never point
`UV_PROJECT_ENVIRONMENT` at system Python or another worktree. Keep Codex, Claude
Code, and the Databricks CLI as separate tools; their credentials do not belong
in the Python environment. Add runtime agent dependencies only when the runtime
chapter needs them. A deployment environment should exclude development groups.

## Repository hygiene

Keep both portfolio tracks and their supporting docs. Remove a file only after
checking its callers and purpose. Ignore environment files, caches, and private
agent preferences. Do not commit `.venv`, credentials, raw session transcripts, or
downloaded tools. Keep the handoff short and current; Git history holds old details.

After a chapter merges, remove its local branch only after the remote chapter
branch is verified and its commits are integrated into `main`. See
[the branch workflow](sentinel/branch-workflow.md). Do not use broad cleanup commands
such as `git clean -fdx`, which can erase ignored environments and local secrets.
