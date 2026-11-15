---
name: adp-platform
description: Implement, verify, deploy-check, evaluate, document, or review Track 4, the Agentic Data Platform (src/adp, config/adp, resources/adp.yml, docs/adp, the azure_dev and azure_ci targets, deploy-azure.yml). Use for any Track 4 code, Azure Databricks, real-model eval, evidence, or diagram work.
---

# Work on Track 4 (Agentic Data Platform)

Paths are relative to the repository root. `AGENTS.md` rules apply on top of this.

## Start

1. Read `docs/sentinel/handoff.md` (current state, next task) and check
   `git status --short --branch`; the checkout wins over any recorded branch.
2. Read `docs/contracts-adp.md` before changing behaviour, plus the ADRs it
   cites (0007–0009). If code and contract disagree, say so before changing either.
3. For orientation, `docs/adp/README.md` is the user guide; the evidence is in
   `docs/adp/live-evidence.md`, `docs/adp/evaluation-results*.md` and
   `docs/adp/azure-setup.md` (verified environment, OIDC, grants, cleanup).

## Authority (agreed with the owner)

Do without asking: edit, run local checks, commit on a branch, push branches,
open PRs, read-only cloud checks (listed below), and merge a PR that changes
only docs/images after its `Unit tests` check passes.

Ask first, naming the exact action: merging any PR that touches `src/`,
`resources/` or `databricks.yml` (CI then deploys Free Edition `dev`), bundle
deploy, job or pipeline runs, Unity Catalog grants or ownership changes, model
deployments, deleting or destroying anything, and any paid model call (state the
model, cases and a `--max-usd` cap). Approval covers the action named, not the
next one. Never print keys or tokens; never commit credentials.

## Local checks (always before a PR)

```bash
uv sync --locked
uv run --locked python -m pytest -q                 # all tracks
uv run --locked python scripts/adp_eval.py          # offline eval (fake agent); CI runs it too
uv run --group agents python -m pytest -q           # also runs the provider tests (anthropic/openai installed)
git diff --check
```

## Read-only cloud checks (allowed)

Databricks (profile `ADP_AZURE`, OAuth; if it is invalid, ask the owner to run
`databricks auth login --host https://adb-7405615454810108.8.azuredatabricks.net --profile ADP_AZURE`):

```bash
databricks bundle validate --target azure_ci --profile ADP_AZURE
databricks jobs list --profile ADP_AZURE -o json
databricks api post /api/2.0/sql/statements --profile ADP_AZURE --json \
  '{"warehouse_id":"edef6a13d7b7a736","catalog":"adb_adp_dev","wait_timeout":"50s","statement":"SELECT ..."}'
gh workflow run deploy-azure.yml --ref main -f deploy=false   # CI: OIDC login + validate only
```

Azure CLI is not installed; run it without installing:
`uvx -q --python 3.13 --from azure-cli az ...` with `AZURE_CORE_COLLECT_TELEMETRY=no`.
The `az databricks` extension fails to install that way; use `az resource show`
and `az rest`. If `az` is logged out, start `az login --use-device-code` in the
background and give the owner the code.

## Gotchas found on this project

- Run CLI commands with an explicit `--target`: inside the bundle root the
  Databricks CLI otherwise uses the default `dev` (Free Edition) host.
- `azure_ci` is production mode and runs as service principal
  `id-adp-github-deploy` (app id `f7545e16-…`), which owns `adp_meta`,
  `adp_bronze`, `adp_gold`. The personal `azure_dev` deployment was destroyed;
  don't redeploy it alongside `azure_ci` (two copies would write the same tables).
- Track 1–3 resources are deployed under `azure_ci` but have no grants for the
  service principal; they fail if run.
- Failing runs are deliberate alerts (incidents end the run red). Serverless
  auto-retry duplicated audit rows once; tasks keep `disable_auto_optimization:
  true` and `max_retries: 0`.
- `information_schema` can lag after ownership changes; confirm with
  `databricks schemas get` / `tables get`. `system.billing` is not readable.
- A shell filter such as `| grep -v ...` returns exit 1 on empty output; confirm
  destructive or create results by reading state back, not by exit code.
- GitHub OIDC subjects for this repo use the immutable form
  `repo:tsogtbatjargal@122837521/bedoux-databricks@1317616316:environment:azure-dev`.

## Real-model evaluation (ask first: it is billed)

`scripts/adp_eval.py --provider claude|azure-openai --max-usd N [--cases ...] --json`.
The budget reserves each call's worst case, so recorded spend cannot pass the cap.
Azure OpenAI: the deployment `adp-eval-gpt-5-4-mini` was deleted; redeploying
`gpt-5.4-mini` (Data Zone Standard, the SKU with quota; gpt-5.4 has none) needs
approval. Pass the key at run time from
`az cognitiveservices account keys list -g rg-adp-dev -n tsogloguli-6913-resource`
via `AZURE_OPENAI_API_KEY`, with `AZURE_OPENAI_ENDPOINT=https://tsogloguli-6913-resource.openai.azure.com/`
and `AZURE_OPENAI_DEPLOYMENT`. Claude needs an Anthropic key the owner provides.
Report each run separately from the fake-agent results, keep earlier runs, and
state run count and variance; one run is one sample.

## Evidence and docs

- A live claim needs the command, inputs, run id and observed result in
  `docs/adp/live-evidence.md`; compare against the local engine for the same
  inputs when possible. Label estimates; never invent numbers.
- Numbers appear in several places: the contract's known gaps, the README Track 4
  section, `docs/adp/README.md`, the eval results file and the diagrams. Change
  them together.
- Diagrams are hand-written animated SVG; follow `docs/adp/diagrams/STYLE.md` and
  check both themes with `scripts/render_svg.sh <svg>` before committing.

## Finish

Update `docs/sentinel/handoff.md` (what changed, checks and results, cloud state,
spend, next task). PR bodies end with the attribution line the session requires;
mention whether merging deploys.
