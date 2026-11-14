# Third-party notices

## Runtime and development dependencies

Declared in `pyproject.toml` and pinned in `uv.lock`; each keeps its own license:
pytest, PyYAML, SQLGlot, DuckDB, and (optional `agents` group) the Anthropic
Python SDK.

## Ideas adapted, no code copied (Track 4)

| Source | What was adapted | How it differs here |
|---|---|---|
| microsoft/fabric-samples, `community-samples/Metadata-driven Ingestion Framework` | Control/audit concepts: per-dataset ingestion metadata, run audit records, watermark advanced after success | Own YAML schema and Python engine; composite cursor and lookback; no T-SQL control tables |
| jackptoke/databricks_citibike_project, `src/shared/canonical.py` | Keeping column mapping and validation as pure Python so it tests without Spark | Own contract types and quarantine reasons |
| databricks/bundle-examples, `default_python` | Bundle target and job layout conventions | This repo's bundle predates Track 4; only a target and a job were added |
| NevedhaAyyanar/AI-powered-Data-Quality-Agent | Idea of a reconciliation tool an agent calls rather than computes | Reconciliation is a tested module; the agent only reads its report |
| microsoft/Modernize-your-code-solution-accelerator (unmaintained) | Idea of reviewing legacy SQL migrations with explicit validation | Deterministic SQLGlot workflow with blockers, rewrite rules and fixture validation |

Licenses of the sources above were not re-verified for this file beyond the
repository pages; verify before reusing any of their code directly.
