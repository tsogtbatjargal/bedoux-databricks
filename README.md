# bedoux-databricks

A Databricks Asset Bundle showcasing lakehouse data engineering across two
tracks: a classic TPC-H medallion benchmark, and an original, Bedoux-branded
analytics domain — both built contracts-first, tested, CI/CD'd, and queryable
through Genie's natural-language BI, entirely within the constraints of
**Databricks Free Edition**.

## Why two tracks

**Track 1 — TPC-H Medallion** is the standard data-engineering benchmark
(bronze/silver/gold over `samples.tpch`), done with real rigor: a locked
contract (`docs/contracts.md`), Auto CDC on genuinely incremental dimensions,
DLT expectations, sequential job orchestration.

**Track 2 — Bedoux Ops & Marketing Analytics** applies the same
contracts-first discipline to an original domain: a fictional small marketing
agency (modeled loosely on what Bedoux actually does — client campaigns, lead
funnels, website engagement — plus a fun meta layer: `ogi`, the agent that
runs Bedoux's own daily-plan and Telegram operations, as its own ops data
source). It exists to show the *engineering pattern generalizes*, not just
that TPC-H can be run once. **All Track 2 data is synthetic and fictional** —
see [`docs/contracts-bedoux.md`](docs/contracts-bedoux.md) for why that's a
deliberate choice, not an oversight.

Full architecture, diagram, and the Free-Edition trade-offs behind each design
choice: [`docs/architecture.md`](docs/architecture.md).

**Track 1 stays, considered and decided.** Removing it was considered and
rejected: Track 1 is where Auto CDC is actually demonstrated against
genuinely incremental data (`customer`/`orders`), and Track 2's own contract
(`docs/contracts-bedoux.md`) explicitly cites it as "the correct place Auto
CDC is demonstrated" when explaining why Track 2's dimensions deliberately
use plain materialized tables instead. Without Track 1 present, that
comparison — CDC used where it fits, skipped where it doesn't — has nothing
to point at. Details on what keeping it means going forward:
[`docs/contracts.md`](docs/contracts.md#track-1-stays).

## The Art of Data Defense

Track 2 is being extended with **Bedoux Sentinel**, a portfolio series about
data quality, sensitive-data handling, and agent-assisted incident
investigation. The theme comes from applying ideas in *The Art of War* to a
modern data platform.

**Chapters 00–04 are integrated into `main`.** Chapter 02 ("Defend before
damage spreads," the publication gate) is deployed and demonstrated live —
a full fault → restore → replay sequence against the real workspace, review-
closed against two follow-on findings. Chapter 03 ("Protect what matters")
is acceptance-complete at code level: its redaction/canary logic is
implemented and unit-tested, guards an append-only evidence log confirmed
live, and — since chapter 04's first increment — a model-call site that
refuses to call its provider when the check fails. That last part is unit-
tested against a fake provider only; no evidence has been sent to a real
model, by design. Chapter 04 ("Investigate and recover") is also
acceptance-complete at code level, not demonstrated live. It covers a
guarded model call, an incident log, cited reports, read-only tools, and
approved recovery with duplicate-free replay, all against a fake provider
and synthetic fixtures. Its before/after business metric and live run are
deliberately deferred. Chapter 05 ("Spend intelligence carefully") is
acceptance-complete at code level, not demonstrated live: its routing
harness runs on fake models only, and its central result, a live
comparison of routing strategies, is deferred. Chapter 06 ("Establish rules
of command") is acceptance-complete at code level, not demonstrated live,
with fake providers only. Chapter 07 ("The complete demonstration") is in
progress: a local, fakes-only end-to-end run tied to the recorded live
evidence, with no new live runs. Build status is tracked
separately from publication status: **no chapter's post has been published
yet**, including chapter 02's, even though it's fully demonstrated. Each
chapter keeps its own retained remote branch as a stable reference; working/
fix branches are removed after merging, chapter branches are not. The full,
current per-chapter status lives in the [series plan](docs/sentinel/README.md)
and [roadmap](docs/sentinel/roadmap.md) — this paragraph is a summary, not
the source of truth.

For development, start with [AGENTS.md](AGENTS.md) and the
[session handoff](docs/sentinel/handoff.md). Codex and Claude Code share the same
project guidance and chapter skills.

## What's demonstrated here

- **Contracts-first modeling** — every layer's naming, grain, and business
  logic is locked in a contract doc before code is written
  ([`contracts.md`](docs/contracts.md), [`contracts-bedoux.md`](docs/contracts-bedoux.md)).
- **Data quality as a real gate, not decoration** — Track 2's generator
  deliberately emits ~2% invalid rows; the DLT expectations in `silver.py`
  actually drop them, provably.
- **Auto CDC used where it fits, skipped where it doesn't** — Track 1 uses it
  for genuinely incremental `customer`/`orders` data; Track 2's dimensions are
  small and fully recomputed each run, so it deliberately uses plain
  materialized tables instead of forcing CDC onto data that doesn't need it.
- **Automated testing** — pure business logic (`src/bedoux/transforms.py`,
  `generator.py`) is unit tested with pytest, independent of any Spark
  cluster or live workspace (`tests/`).
- **CI/CD** — GitHub Actions runs locked local tests on every PR and push to
  `main`. Pipeline/bundle changes also validate, then deploy on `main`.
  Documentation and tooling changes alone do not deploy. Manual dispatch has
  separate deployment and pipeline-run options (`.github/workflows/ci.yml`).
- **A BI layer, not just pipelines** — both tracks' Gold layers are queryable
  through Genie's natural-language interface ([`docs/genie.md`](docs/genie.md)).
- **Honest engineering trade-offs under Free Edition** — see below. A senior
  reviewer respects a named constraint more than a pretended one.

## Databricks Free Edition trade-offs

This project runs on [Databricks Free Edition](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations),
which is serverless-only, non-commercial, and quota-limited. Concretely, that shaped:

| Constraint | How this project handles it |
|---|---|
| One SQL warehouse, fixed 2X-Small | Both Genie spaces share it |
| Max 5 concurrent job tasks; one active Lakeflow pipeline per type | Sequential jobs; Track 2 adds a publication gate between Silver and Gold. Operators must avoid concurrent pipeline/job runs |
| No account console; service principals unproven | Personal access tokens are available and verified in this workspace, so CI stays on a PAT (`DATABRICKS_HOST` + `DATABRICKS_TOKEN`). No service principal exists; in a paid workspace this would be OIDC + a service principal. See the [live verification runbook](docs/sentinel/live-verification.md) |
| Non-commercial use only | Track 2 is explicitly fictional/synthetic data, never Bedoux's real business data |
| Compute-quota shutdown risk | No auto-schedule on either job — manual trigger or `workflow_dispatch` only |

## Project layout

```
AGENTS.md                       # shared agent instructions (Codex + Claude Code)
CLAUDE.md                       # Claude Code entry point; imports AGENTS.md
pyproject.toml, uv.lock         # declared and locked local Python dependencies
.python-version, mise.toml      # Python selection and optional uv tool bootstrap
databricks.yml                  # bundle definition (target: dev)
resources/
  pipelines.yml, jobs.yml         # Track 1 (TPC-H)
  bedoux_pipelines.yml, bedoux_jobs.yml   # Track 2 (Bedoux)
src/
  bronze.py, silver.py, gold.py    # Track 1 DLT pipeline source
  bedoux/
    generator.py                   # deterministic synthetic data (no external deps)
    transforms.py                  # pure business-logic functions, unit tested
    bronze.py, silver.py, gold.py  # Track 2 DLT pipeline source
tests/                            # pytest, no Spark/workspace dependency
docs/
  contracts.md, contracts-bedoux.md   # locked layer/naming/business rules per track
  architecture.md, architecture.drawio  # diagram + design rationale
  ai_rules.md                       # pointer to AGENTS.md (superseded)
  genie.md                          # Genie CLI usage + space setup
  sentinel/                         # Art of Data Defense: roadmap, workflow, handoff,
                                   #   live-verification runbook, chapters
.agents/skills/                    # shared chapter/story skill bodies
.claude/skills/                    # Claude Code adapters onto those same bodies
.codex/config.toml                 # Codex project settings (reasoning effort only)
scripts/genie.sh                   # thin wrapper over `databricks genie ...`
.github/workflows/ci.yml           # local tests always; workspace jobs gated by changes
```

## Getting started

Install [uv](https://docs.astral.sh/uv/getting-started/installation/), then run the
local tests in the project's isolated environment. See
[Local development](docs/development.md) for mise setup and dependency changes.

```bash
# Local checks (no live workspace needed)
uv sync --locked
uv run --locked python -m pytest -q
```

Workspace commands use a separately installed Databricks CLI and credentials:

```bash
databricks auth login --host https://dbc-3f70aae3-11d5.cloud.databricks.com --profile bedoux-databricks
databricks bundle validate --profile bedoux-databricks

# Deploy + run (touches the live workspace — see docs/architecture.md for the
# Free Edition trade-offs this implies)
databricks bundle deploy --profile bedoux-databricks
databricks bundle run tpch_medallion_pipeline_job --profile bedoux-databricks
databricks bundle run bedoux_analytics_job --profile bedoux-databricks
```

> **Note on the live resources:** Track 1's pipelines/job already exist in the
> workspace, created outside this bundle. Deploying as-is creates a separate,
> parallel set under the bundle's own workspace path rather than touching the
> existing ones. To have this bundle manage the existing live resources
> instead, bind them first (one-time, per resource):
>
> ```bash
> databricks bundle deployment bind pipeline bronze_pipeline db327b4b-8c23-44db-81dc-45e391400409 --profile bedoux-databricks
> databricks bundle deployment bind pipeline silver_pipeline d9ec9428-71e3-4e80-a198-20b99e580e10 --profile bedoux-databricks
> databricks bundle deployment bind pipeline gold_pipeline fd829e23-9f1b-4076-bce7-f70e78bd7e91 --profile bedoux-databricks
> databricks bundle deployment bind job tpch_medallion_pipeline_job 69931271264753 --profile bedoux-databricks
> ```
>
> Review the resulting plan carefully before confirming — binding then
> deploying makes the bundle's config authoritative over the live resource.
> Track 2's resources are new, so no binding is needed there.

## Genie

Both tracks have a live Genie space over their Gold layer, sharing the one available
2X-Small warehouse: **TPC-H Medallion Analytics** (`01f18c57fa251338962ee7a34efab97e`)
and **Bedoux Ops & Marketing Analytics** (`01f18c5765861b98a829e34fcec67160`). See
[`docs/genie.md`](docs/genie.md) for CLI usage, the exact `serialized_space` JSON used
to create each, and sample questions verified end-to-end.
