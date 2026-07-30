# bedoux-databricks

Databricks Asset Bundle (DAB) for the TPC-H Medallion pipeline, as a git-tracked local
counterpart to the workspace project at
`/Users/tsoglog.uli@gmail.com/Databricks-DE-TB-Project`.

## Layout

```
bedoux-databricks/
  databricks.yml          # bundle definition (target: dev)
  resources/
    pipelines.yml          # bronze_pipeline, silver_pipeline, gold_pipeline (DLT)
    jobs.yml                # tpch_medallion_pipeline_job (bronze -> silver -> gold)
  src/
    bronze.py, silver.py, gold.py   # DLT pipeline source, one file per layer
  docs/
    contracts.md            # layer rules, naming conventions, business logic (source of truth)
    ai_rules.md              # development/AI guardrails for this project
    genie.md                 # Genie CLI usage for this workspace
  scripts/
    genie.sh                 # thin wrapper over `databricks genie ...`
```

## Architecture

Medallion pattern on Unity Catalog catalog `workspace`, source `samples.tpch`:

- **Bronze** (`workspace.bronze`) — 8 raw, append-only tables (`<source>_raw`)
- **Silver** (`workspace.silver`) — 8 cleaned/validated tables (`<source>_clean`), Auto CDC on `customer`/`orders`
- **Gold** (`workspace.gold`) — 3 business tables (`gold_*`): monthly revenue by region, customer lifetime value, top products

Full rules: [`docs/contracts.md`](docs/contracts.md).

## Prerequisites

```bash
databricks auth login --host https://dbc-3f70aae3-11d5.cloud.databricks.com --profile bedoux-databricks
# or: databricks configure --token --profile bedoux-databricks
```

## Common commands

```bash
# Validate the bundle (safe, read-only)
databricks bundle validate --profile bedoux-databricks

# See what would change vs. the live workspace
databricks bundle deploy --profile bedoux-databricks --dry-run   # not all CLI versions support this; validate + review plan output on deploy

# Deploy (creates/updates bundle-managed pipelines + job under
# /Workspace/Users/tsoglog.uli@gmail.com/.bundle/bedoux_databricks/dev)
databricks bundle deploy --profile bedoux-databricks

# Run the orchestration job
databricks bundle run tpch_medallion_pipeline_job --profile bedoux-databricks
```

> **Note:** the live pipelines (`bronze_pipeline`, `silver_pipeline`, `gold_pipeline`,
> `tpch_medallion_pipeline_job`) already exist in the workspace, created outside this bundle.
> Deploying this bundle as-is will create a **separate, parallel set** of resources under the
> bundle's own workspace path — it will not touch the existing ones. To have this bundle manage
> the existing live resources instead, bind them first (one-time, per resource):
>
> ```bash
> databricks bundle deployment bind pipeline bronze_pipeline db327b4b-8c23-44db-81dc-45e391400409 --profile bedoux-databricks
> databricks bundle deployment bind pipeline silver_pipeline d9ec9428-71e3-4e80-a198-20b99e580e10 --profile bedoux-databricks
> databricks bundle deployment bind pipeline gold_pipeline fd829e23-9f1b-4076-bce7-f70e78bd7e91 --profile bedoux-databricks
> databricks bundle deployment bind job tpch_medallion_pipeline_job 69931271264753 --profile bedoux-databricks
> ```
>
> Review the resulting plan carefully before confirming — binding then deploying will make the
> bundle's config authoritative over the live resource.

## Genie

See [`docs/genie.md`](docs/genie.md) and `scripts/genie.sh`.
