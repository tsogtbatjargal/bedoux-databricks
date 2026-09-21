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

## The Art of Data Defense

I'm extending Track 2 with **Bedoux Sentinel**, a portfolio series about data
quality, sensitive-data handling, and agent-assisted incident investigation.
The theme comes from applying ideas in *The Art of War* to a modern data platform.

The [series plan](docs/sentinel/README.md) separates existing behavior from the
capabilities still to build. Each chapter will have a retained branch and a stable
post reference; `main` will accumulate the completed work. The finale will show
one incident from detection through recovery.

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
- **CI/CD** — GitHub Actions runs tests + `bundle validate` on every PR,
  `bundle deploy` on merge to `main`, and a manual `workflow_dispatch` button
  to trigger the pipeline job (`.github/workflows/ci.yml`).
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
| Max 5 concurrent job tasks; one active Lakeflow pipeline per type | Both jobs are strictly sequential (bronze → silver → gold), never triggered concurrently |
| No account console / service principals | CI/CD uses a personal access token as a GitHub secret — in a paid workspace this would be OIDC + a service principal |
| Non-commercial use only | Track 2 is explicitly fictional/synthetic data, never Bedoux's real business data |
| Compute-quota shutdown risk | No auto-schedule on either job — manual trigger or `workflow_dispatch` only |

## Project layout

```
AGENTS.md                       # shared agent instructions (Codex + Claude Code)
CLAUDE.md                       # Claude Code entry point; imports AGENTS.md
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
  sentinel/                         # Art of Data Defense: roadmap, workflow, handoff
.agents/skills/                    # shared chapter/story skill bodies
.claude/skills/                    # Claude Code adapters onto those same bodies
.codex/config.toml                 # Codex project settings (reasoning effort only)
scripts/genie.sh                   # thin wrapper over `databricks genie ...`
.github/workflows/ci.yml           # test -> validate -> deploy -> (manual) run
```

## Getting started

```bash
databricks auth login --host https://dbc-3f70aae3-11d5.cloud.databricks.com --profile bedoux-databricks

# Local checks (no live workspace needed)
pip install -r requirements-dev.txt
pytest tests/ -v
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
