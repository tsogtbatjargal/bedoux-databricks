# Live verification runbook

Chapter 02 is implemented and locally tested, **not demonstrated**. Section 1
is now satisfied: local CLI access exists and read-only checks have run against
the live workspace. Nothing in sections 3 and 4 has been executed — no deploy,
no job run, no runtime evidence.
Read [handoff.md](handoff.md) for current checkpoints and authorization limits.

## 1. Access without widening deployment authority

A live demo does not require storing credentials in GitHub first. With the
user's approval, interactive local OAuth can validate and operate the same
bundle; GitHub CI authentication is a separate setup task.

**Local access is established.** The official CLI is pinned in `mise.toml`
under the explicit `github:databricks/cli` backend — not the unrelated legacy
Python package, and not inside the uv environment — and the user completed
[OAuth user login](https://docs.databricks.com/aws/en/dev-tools/auth/oauth-u2m)
under the named profile `bedoux-databricks`. See
[development.md](../development.md) for the exact install, login, and verify
commands. Do not share tokens or authentication caches. A browser login is not
unattended CI authentication.

**Credential capability, determined 2026-09-21** by read-only API calls under
that profile. The [Free Edition limitations](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
page does not answer this; the workspace itself does.

| Method | What was observed | Consequence |
|---|---|---|
| PAT | `tokens list` and the admin `token-management list` both succeeded, returning two existing tokens | PATs work here. The workflow's existing `DATABRICKS_HOST` + `DATABRICKS_TOKEN` wiring needs no change |
| Service principal / OAuth M2M | `service-principals list` returned an empty list (exit 0) | The SCIM endpoint answers, but no service principal exists. Creating one is a write action and was not attempted, so M2M remains unproven |
| Admin rights | `current-user me` shows group `admins` | The user can create and revoke tokens themselves; no account console is needed for this |

**CI therefore stays on a PAT.** No workflow edit is required, and
`run_as.user_name` stays the person who owns the token. Swapping to M2M later
would mean reviewing the workflow and the bundle `run_as` identity together,
not just renaming secrets.

Two tokens already exist: `bedoux-databricks-project` (created 2026-07-30,
expires 2027-07-30) and `CLI Access Token` (created 2026-09-21, expires
2027-09-21). Confirm you recognize both before reusing either, and revoke any
you do not — a year-long token you cannot account for is itself a finding.
Report only the capability found, never the credential.

The user sets approved secrets through GitHub's UI or the interactive
[GitHub CLI prompt](https://cli.github.com/manual/gh_secret_set):

```bash
gh secret set DATABRICKS_HOST
gh secret set DATABRICKS_TOKEN
gh secret list
```

Do not put literal secrets in shell commands, files in the repo, chat, or logs.
Use a bounded token lifetime and revoke it when no longer needed. Compromised
credentials must be rotated; deleting a message is not sufficient.

## 2. What credentials enable

The existing workflow policy is unchanged:

- Every PR/main push/manual dispatch runs local tests.
- Bundle-path PRs also validate; PRs never deploy.
- Bundle-path pushes to main validate, then deploy **only if checks succeed**.
- Docs/tooling-only pushes run local tests and skip workspace jobs.
- Manual dispatch validates; `deploy` opts into deployment and `run_job`
  additionally opts into execution. The selected branch supplies the code.

Adding credentials does not trigger deployment by itself. It enables later
eligible runs or reruns to reach the workspace. Authentication can expose
further configuration errors; it does not guarantee validation succeeds.

Before enabling this, the user chooses whether to retain automatic deployment
on bundle-path main merges or request a separate deployment-policy change.
Do not bypass validation failures or convert them to green to unblock the PR.

`bundle deploy` updates definitions; `bundle run` executes the job. The bundle
includes **both tracks**, so a full deployment can create/update Track 1
resources even though this change edits only Track 2. Review the bundle scope
and existing resource ownership before deployment; do not bind or delete
existing workspace resources implicitly.

## 3. Preconditions for this small demonstration

### Observed starting state (read-only, 2026-09-21)

The `dev` target is not empty, and that changes what this demo can show:

- `[dev tsoglog_uli] bedoux_analytics_job` exists with `max_concurrent_runs: 1`,
  but its **deployed task graph is the pre-chapter-02 one**: bronze → silver →
  gold, with no `bedoux_gate_task`. The gate exists only in this checkout. The
  first deploy is therefore what introduces it.
- All three `workspace.bedoux_gold.*` tables already exist, last written
  2026-07-30. That is a real published baseline, which makes stage 2's
  retention claim checkable rather than vacuous: if the gate withholds, their
  content and `updated_at` must be unchanged afterwards.
- Because a baseline exists, the **first-ever-run** case cannot be shown in
  `dev` without destroying it. Leave that as a design argument, not a stage.

- User authorizes the actual target, full-bundle deployment scope, and synthetic
  Track 2 runs. No merge is needed to test the chapter branch.
- Use the same profile, target, and bundle identity throughout; alternate
  deployments must not write the same hard-coded Track 2 schemas.
- Confirm `max_concurrent_runs: 1` on the deployed job. No direct pipeline
  runs, other writers, deployments mid-run, or repair-only runs during the demo.
- The gate checks timestamp freshness, **not immutable run/batch identity**.
  Another writer's newer data could pass. This demo is not a concurrency or
  permissions guarantee. Direct Gold runs bypass the gate.
- The documented [serverless notebook configuration](https://docs.databricks.com/aws/en/dev-tools/bundles/examples)
  allows omission of cluster settings. Notebook `base_parameters` and
  [`job.start_time.timestamp_ms`](https://docs.databricks.com/aws/en/jobs/dynamic-value-references)
  are documented. Keep the notebook task unless an actual error says otherwise.
- The gate converts `_computed_ts` with SQL
  [`unix_millis`](https://docs.databricks.com/aws/en/sql/language-manual/functions/unix_millis)
  before collecting it, then compares timezone-aware UTC datetimes. Missing
  or unresolved run context must fail, not disable checking.

## 4. Baseline → withheld → restored → replay

The override is implemented: bundle variable `bedoux_lead_invalid_rate`
sets Bronze configuration `bedoux.lead_invalid_rate`. Default `0.02`;
demonstration fault `0.30`. Only leads change. Values outside 0..1, NaN,
infinity, and malformed strings are rejected.

This is a **deployment-time** setting, not a run-time job parameter. Changing
`--var` only on `bundle run` does not update the deployed pipeline.
For each stage, validate and deploy the selected value, then run the full job.
Example for the healthy stage, only after authorization:

```bash
databricks bundle validate -t dev --profile bedoux-databricks --var bedoux_lead_invalid_rate=0.02
databricks bundle deploy -t dev --profile bedoux-databricks --var bedoux_lead_invalid_rate=0.02
databricks bundle run bedoux_analytics_job -t dev --profile bedoux-databricks --var bedoux_lead_invalid_rate=0.02
```

1. **Baseline (0.02):** all four tasks should succeed. Save the three
   `gate_status` rows, clean/quarantine counts, and full Gold content evidence.
2. **Fault (0.30):** repeat validate/deploy/run with 0.30. Bronze/Silver should
   succeed, leads should exceed 10%, gate should fail, and Gold should not run.
   Check all three Gold tables against the baseline, not just their row counts.
   A failure before the gate is not a successful defense demonstration.
3. **Restore (0.02):** explicitly redeploy 0.02 and run the full job. Confirm
   the deployed setting was restored and all tasks succeed. A fixed seed
   restores business rows, not audit timestamps.
4. **Replay:** run the full healthy job again without changing configuration.
   Compare business content and multiplicities, excluding documented audit
   fields such as `_ingest_ts`, `_quarantined_ts`, and `_computed_ts`.

**Restoration is required.** The bad-rate deployment persists if the session
stops after stage 2. Record that fact immediately in the handoff. Do not call
this a demo with no cleanup. Capture quarantine and failed-run evidence before
restoring: these recomputed tables are not an append-only incident archive.

For the small synthetic Gold tables, capture counts, schema, and an
order-independent content digest in a separate read-only notebook. Save the
baseline output before injecting faults and compare all three outputs:

```python
import hashlib
import json

for name in ("gold_campaign_performance", "gold_client_funnel", "gold_ogi_ops_health"):
    frame = spark.table(f"workspace.bedoux_gold.{name}")
    rows = sorted(
        json.dumps(row.asDict(recursive=True), sort_keys=True, default=str)
        for row in frame.collect()
    )
    payload = json.dumps({"schema": frame.schema.json(), "rows": rows}, sort_keys=True)
    print(name, len(rows), hashlib.sha256(payload.encode()).hexdigest())
```

Counts alone can hide changed values. An unchanged digest plus skipped Gold
task supports retention for these fixtures. For restored/replayed floating
aggregates, investigate any digest difference and compare values with an
explicit tolerance if numerical aggregation order differs; never silently
replace content checks with count checks.

Record job/run IDs, resolved gate parameters, per-task results, gate evidence,
and content comparisons in the chapter evidence. Local tests/stubs do not
substitute for any of these observations. If a refresh reuses old gate evidence,
the freshness check must stop Gold; investigate pipeline refresh semantics
rather than weakening the check.

## 5. What remains unproved

Workspace authentication and `bundle validate --target dev` have now both
succeeded locally. Everything downstream of them is still unverified: notebook
import paths, serverless execution of a notebook task, SQL timestamp
conversion, orchestration withholding, and Gold retention/replay. Validation
checks definitions, not behavior.

Even a successful demonstration does not establish immutable batch binding,
atomic multi-table publication, or an authorization boundary. A first-run
failure should also be tested in a separately authorized empty destination;
do not drop baseline tables to manufacture that scenario.
