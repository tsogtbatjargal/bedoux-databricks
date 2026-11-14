# Session handoff

This is the technical handoff. Check Git before continuing; recorded state is
context, not authorization to merge, deploy, publish or call paid APIs.

## Current implementation

Chapters 00–07 are integrated at code level. **372 local tests pass**
(`uv run --locked python -m pytest -q`, run on `docs/separate-editorial-content`
before commit). The editorial separation changes no Python, tests, dependencies,
resources or bundle configuration.

- **02:** live fault, restore and replay evidence is recorded in
  [chapter-02-evidence.md](chapter-02-evidence.md).
- **03:** redaction/canary checks are local. The append-only Delta evidence log
  is demonstrated live, including failed UPDATE/DELETE and duplicate rows on
  retry. See [chapter-03-evidence.md](chapter-03-evidence.md).
- **04–06:** investigation, bounded tools, approval/replay, routing and adversarial
  boundaries use scripted providers and local fixtures. No real model has been
  called; real executors, table readers and provider evaluation remain deferred.
- **07:** `scripts/full_demo.py` provides a reproducible local example using
  fakes, tied to historical Databricks evidence. It does not demonstrate a live
  agent, redaction in the complete path or the composed finale. See
  [chapter 07](chapters/07-full-demo.md) and [known gaps](known-gaps.md).

Detailed acceptance maps and technical history remain in
[the chapters](README.md#start-here) and [roadmap](roadmap.md).
Do not promote code-level completion into a live-evidence claim.

## Latest change: Track 4 deployed to Azure Databricks and merged

`azure_dev` now targets workspace `adb-adp-dev`
(`https://adb-7405615454810108.8.azuredatabricks.net`, catalog `adb_adp_dev`);
inventory in `docs/adp/azure-setup.md`. With the user's approval: bundle
deployed (13 resources, all serverless, manual-trigger) and `adp_platform_job`
run four times (day 1, day 2, day 2 repeat, day 3 + `bad_unit_price`). Results
equal the local engine; evidence in `docs/adp/live-evidence.md`. A US$50/month
Azure budget alert (`adp-dev-monthly-50`, email to Owners) was created; it does
not cap spend.

Finding fixed: serverless auto-retry re-ran a failed reconcile task and
duplicated audit/incident rows; `resources/adp.yml` now sets
`disable_auto_optimization: true`, `max_retries: 0` (deployed, not yet
exercised by a failing run). Checks: pytest 480 passed; `bundle validate`
for `azure_dev` OK. `dev` (Free Edition) validate not rerun: its token is
still invalid.

Local tooling: Azure CLI is not installed; it ran via
`uvx --python 3.13 --from azure-cli az` (the `databricks` az extension fails
to install that way; use `az resource` / `az rest`). Credit: US$200 sign-up
credit, expires 2026-12-13. Trial SKU ends about 2026-11-28. NAT gateway +
public IP in the managed resource group bill hourly while the workspace exists.

PRs: #33 (Track 3) and #34 (Track 4, base `main`, depends on #33), both
pushed with the user's approval; CI `Unit tests` and `Validate bundle` (Free
Edition `dev`, stored secrets) passed on both. The user merged both on
2026-11-13: #33 → `35a4951` (CI run 43542939016), #34 → `edd76f8` (CI run
43543041793); unit tests, validate and Free Edition deploy succeeded each time.
Remote branches `track3/01-contract-generator` and `track4/01-agentic-platform`
are kept.

Retry fix verified in Azure (run `910590590998406`, attempt 0 only, one audit
row per incident; `docs/adp/live-evidence.md`). GitHub OIDC set up the
Azure-native way, because the workspace owner is not a Databricks account admin:
managed identity `id-adp-github-deploy` + federated credential (immutable
subject), added as a workspace service principal with no UC grants; GitHub
environment `azure-dev` (main only). `deploy-azure.yml` now uses `azure/login`
and `DATABRICKS_AUTH_TYPE: azure-cli` (#36, merged). Validate-only dispatch
succeeded as the service principal (run 43550611869) after granting it the
`workspace-access` entitlement.

CI now deploys and runs: target `azure_ci` (#38, production mode, `run_as` the
service principal); the SP owns the Track 4 schemas/tables; the personal
`azure_dev` deployment was destroyed (all user-approved). Workflow run
43552132296 deployed and ran job `1023469102611052` (run `892095403308316`),
matching the local engine (`docs/adp/live-evidence.md`). Re-validated runs:
43551167534 (identity step fixed by #37).

Real-model eval (user chose Azure OpenAI on the Azure credit instead of an
Anthropic key): deployment `adp-eval-gpt-5-4-mini` (gpt-5.4-mini, Data Zone
Standard, 100k TPM, pay-per-token, no standing charge) on AI Services
`tsogloguli-6913-resource`; gpt-5.4 had 0 real-time quota. New
`src/adp/azure_openai_provider.py`, `src/adp/budget.py` (hard cap: reserve the
worst case before each call), eval `--provider azure-openai|claude --max-usd
--cases`. Result, all 30 cases, $0.17 of a $5 cap: 13 reported (all correct,
routed), 17 pending (15 `redacted_citation` from citing empty containers such as
`schema_diff.added -> []`, 2 `unresolved_citation`), 0 forbidden tools.
Results: `docs/adp/evaluation-results-azure-openai.md`. Key passed from
`az cognitiveservices account keys list` at run time; never stored.

Next useful task: user decision on the citation guard: allow citing an empty
container that was visible as empty (keep refusing all-redacted ones, give it
its own reason code), then re-run the Azure eval and report both runs. Claude
eval still needs an Anthropic key. Track 1–3 resources under `azure_ci` have no
SP grants and would fail if run. If the
workspace is no longer needed after the demo, deleting `adb-adp-dev` removes
the managed resource group and its hourly charges (destructive; user's call).

## Latest change: Track 4 started (branch `track4/01-agentic-platform`)

Branched from `track3/01-contract-generator` at `28b1195` (Track 3 is a
dependency: `adp` reuses `aglc.reconcile` and `aglc.governance.ident`). Not
merged and not pushed. Merging to `main` deploys (CI), so integrating is a
deployment decision; merge Track 3 first or together.

Added: `docs/contracts-adp.md`; ADRs `0007`–`0009`; `config/adp/datasets/`
(orders, order_lines, payments); `src/adp/` (metadata, contracts, generator,
ingest, reconcile, pipeline, investigator, fakes, runbooks, modernize,
claude_provider, two notebook tasks); `migrations/adp/` (22 SQL cases, DuckDB
fixtures); `resources/adp.yml` (`adp_platform_job`); `azure_dev` target in
`databricks.yml` (placeholder host); `.github/workflows/deploy-azure.yml`
(manual, GitHub OIDC); `scripts/adp_demo.py`, `scripts/adp_eval.py`;
`tests/test_adp.py`, `tests/fixtures/adp_incident_cases.json`;
`docs/adp/azure-setup.md`, `docs/adp/evaluation-results.md`;
`THIRD_PARTY_NOTICES.md`. Dev deps: sqlglot, duckdb, pyyaml; optional group
`agents`: anthropic. CI's unit-test job now also runs the offline eval.

Checks: `uv run --locked python -m pytest -q` → **480 passed** (418 + 62
Track 4). `uv run --locked python scripts/adp_eval.py` → 30/30 incidents opened
and routed, 0 forbidden tool executions, detection recall 144/144 seeded rows,
22/22 SQL statuses as expected, 0 must-flag SQL accepted (fake provider; see
the results file for what that does and doesn't measure).
**Not run:** `databricks bundle validate` (CLI refresh token invalid, same as
Track 3), any deploy or job run, any Azure step, any real model call.

Review finding fixed during the build: `sql17` (`DATEDIFF(month)`) validated
locally although Databricks counts whole months and T-SQL counts boundaries;
DuckDB shares the T-SQL behaviour, so the second transpilation hid it. A
hazard rule now blocks non-day `DATEDIFF` units.

Next useful task: set the real Azure host and catalog in `azure_dev`,
`databricks auth login`, `bundle validate --target azure_dev`, deploy, run
`adp_platform_job` for days 1–3, then day 3 with `defect=bad_unit_price`, and
record the evidence (run ids, row counts, incident rows) in
`docs/adp/live-evidence.md`. Verify PyYAML is importable on serverless
notebooks. Then: one opt-in Claude eval run with a spend cap, recorded via
`scripts/adp_eval.py --provider claude --write`.

## Latest change: Track 3 started (branch `track3/01-contract-generator`)

Branched from `main` at `3675ff5`. Not merged and not pushed. Merging to `main`
deploys (CI), so integrating is a deployment decision.

Added: `docs/contracts-aglc.md`; `docs/adr/0001`–`0006`; `src/aglc/` (generator,
expectations, rules, legacy, reconcile, governance, DLT bronze/silver/gold, three
notebook tasks); `resources/aglc.yml` (3 pipelines + `aglc_lakehouse_job`); three
`aglc_*` variables in `databricks.yml`; `tests/test_aglc.py`.

Checks: `uv run --locked python -m pytest -q` → **418 passed** (372 existing + 46
Track 3). `py_compile` on all `src/aglc/*.py`, YAML parse and `git diff --check` clean.
**Not run:** `databricks bundle validate` (the CLI profile `bedoux-databricks` shows
`Valid: NO`, so re-login is needed), any deploy or job run.

Implemented, not demonstrated live: Spark Gold mirroring `rules.py`; DLT column
masks and row filter (Free Edition support unverified, `aglc_enforce_governance`
toggles them); reconcile gate; grants (off by default, `aglc_apply_grants`).

Next useful task: re-login, `databricks bundle validate`, deploy to dev, run
`aglc_lakehouse_job` once with `aglc_enforce_governance=true`. If masks or filters
are unsupported, rerun with `false` and record that in ADR 0004. Then: a parity
check of `gold_rg_player_flags` against `rules.player_flags`, a dev/prod target
split (per-target catalog or schema prefix, since one Free Edition workspace),
a Genie space over RG Gold, a diagram, and a 2-minute demo script.

## Latest change: editorial separation

Delivered from the working branch `docs/separate-editorial-content`, based on
`ede2901766fddbe40263ee601aa3d8eee37a8491`, through a documentation-only PR.

At the user's request, editorial material moved to the separate
`bedoux-sentinel-content` workspace: seven post drafts, the final video script,
writing guidance, inspiration notes, introduction SVG and storytelling skill.
Copies were verified before removal. That workspace's README and migration
record identify the destinations and original source commit.

This repo retains technical chapter records, runbooks, evidence, the architecture
source, reproducible demo, AGENTS.md, CLAUDE.md and the shared chapter skill with
its Claude adapter. The existing `.codex/config.toml` remains on disk but is
removed from tracking and ignored because it only holds a personal preference.
See [repository scope](repository-scope.md).

Chapter 00's title is "Shared development setup" in the roadmap, the series
README and the chapter doc; the former roadmap title, "The challenge", was
editorial framing.

Retained remote chapter snapshots are untouched; they still include their
historical editorial material. The external content folder is not a Git repo
and has no configured remote. Pushing this repo does not back it up.

## Verification

Migration copy checks passed for all eight extracted draft/script sections and
the moved writing guide, SVG, adapter and inspiration text. A final check of
relative links and heading anchors in all Markdown files found 135 links, none
broken. Both shared skills and both
Claude adapters passed the skill validator; their file references and CLAUDE
imports resolve. Fresh-session discovery was not exercised.

The local Codex config is unchanged, valid TOML, untracked and ignored. Diff
whitespace checks passed. Runtime, tests, demo, dependencies, bundle/CI, live
evidence and the technical diagram are unchanged; pytest passed (372) and live
validation was not run. No job or provider was called.

## Branches and next step

- Remote: `main` and the eight retained chapter branches, `series/00-introduction`
  through `series/07-full-demo`. The working branch `docs/separate-editorial-content`
  was deleted after merging.
- Local: `main` only.

Wait for `Unit tests` on a PR's head before merging, documentation-only included.

Preserve/version the external content workspace; it has no Git remote.
Existing drafts there still
need an editorial status review before publication. Technical architecture
updates and all live provider work remain separate tasks.
