# Live verification runbook

Chapter 02 built a publication gate that has never run. Every check so far is a
policy test over in-memory rows: they prove what the gate *decides*, not that
Spark produces the evidence, that the job graph stops Gold, or that a withheld
table keeps its data. This runbook covers what has to happen before chapter 02
can honestly be called demonstrated.

Nothing here has been executed. No credentials exist in this environment and
none were created. The steps requiring workspace access are the user's to run.

## 1. Determine which authentication this workspace actually supports

**Do not assume.** The repository's README currently says Free Edition has "no
account console / service principals" and that CI uses a personal access token.
That predates this chapter and has not been re-checked. Meanwhile:

- The [Free Edition limitations page](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
  says nothing about PATs, service principals, or API access. Its only
  authentication statement concerns *user sign-in*: "Authentication is limited
  to email OTP, Sign in with Google, and Sign in with Microsoft. No SSO or SCIM
  support."
- The current [authentication docs](https://docs.databricks.com/aws/en/dev-tools/auth/)
  lead with OAuth and present **OAuth M2M with a service principal** as the
  method for "fully automated and CI/CD workflows". They do not describe PATs
  as removed, but PATs are no longer the documented default.

So there are two plausible paths and the docs do not tell us which one this
workspace allows. Check it directly, in the workspace UI:

1. **PAT available?** Settings → Developer → Access tokens. If token generation
   is present and not disabled by an admin setting, a PAT works with the
   workflow exactly as written today (`DATABRICKS_HOST` + `DATABRICKS_TOKEN`).
2. **Service principal available?** Settings → Identity and access → Service
   principals. Free Edition has no account console, so this may be absent
   entirely. If a service principal *can* be created with an OAuth secret, that
   is the better CI credential — it is not tied to a person and can be scoped.

Report only **which option exists**. Never paste a token, secret, client ID, or
workspace URL with embedded credentials into a chat, an issue, a commit, or a
model request.

**If only OAuth M2M is available, the workflow needs a change before it can
authenticate.** It currently passes `DATABRICKS_TOKEN` only:

```yaml
env:
  DATABRICKS_HOST: ${{ secrets.DATABRICKS_HOST }}
  DATABRICKS_TOKEN: ${{ secrets.DATABRICKS_TOKEN }}
```

OAuth M2M instead needs `DATABRICKS_CLIENT_ID` and `DATABRICKS_CLIENT_SECRET`
(with `DATABRICKS_HOST` unchanged). That edit is *not* made yet, deliberately —
it should be made once, against whichever method the workspace actually
supports, rather than speculatively supporting both.

## 2. Set the secrets without exposing them

Whoever holds the credential sets it. An assistant must not create, request,
read, echo, or commit one.

```bash
# Prompts for the value; nothing lands in shell history or the terminal scrollback.
gh secret set DATABRICKS_HOST
gh secret set DATABRICKS_TOKEN          # PAT path
# or, for the OAuth M2M path:
gh secret set DATABRICKS_CLIENT_ID
gh secret set DATABRICKS_CLIENT_SECRET

gh secret list                          # confirms names and dates only, never values
```

Notes:

- `DATABRICKS_HOST` is not itself a secret (it is already in `databricks.yml`),
  but the workflow reads it from secrets, so it must be set there too.
- Never use `echo "$TOKEN" | gh secret set ...` in an interactive shell — that
  puts the value in history. Use the prompt, or `--body-file` with a file you
  delete afterwards.
- If a token is ever pasted somewhere it should not be, rotate it rather than
  deleting the message. Assume anything pasted is compromised.
- Local workspace access, if wanted, belongs in `~/.databrickscfg` or
  `databricks auth login` — never in the repository, `.env`, or a committed file.

## 3. Know what happens automatically once secrets exist

Right now, with no secrets, the chain is inert: `Validate bundle` fails on
authentication, and because `Deploy bundle` has `needs: [validate, changes]`, a
failed validate **skips** deploy. Nothing reaches the workspace. This has been
true for the repository's whole history — the pre-series run `30594756421` from
July failed with the identical auth error.

Adding secrets changes that, immediately and without further prompting:

| Event | Before secrets | After secrets |
| --- | --- | --- |
| PR touching `src/**`, `resources/**`, `databricks.yml` | validate fails (red), no deploy | validate runs for real; still **never** deploys |
| Push/merge to `main` touching those paths | validate fails, deploy skipped | validate passes, then **`databricks bundle deploy --target dev` runs automatically** |
| Push to `main` touching only docs/tooling | workflow skipped | workflow skipped (unchanged) |
| Manual dispatch with `deploy` unchecked | validate fails | validate only |
| Manual dispatch with `deploy` checked | validate fails, deploy skipped | deploys |

So **merging PR #3 after secrets are configured deploys the bundle to the dev
target automatically.** That is a real deployment decision and needs explicit
authorization at that moment; it is not implied by having set up credentials.

One nuance that matters for the demonstration: `bundle deploy` creates and
updates the pipelines and job definitions. It does **not** run them. The
workflow only runs `bedoux_analytics_job` on a manual dispatch with `run_job`
checked. So deploying does not by itself execute the gate or touch table data.

## 4. The demonstration: baseline, withheld, restored

The goal is a run where the gate actually withholds, observed rather than
argued. Three stages, all synthetic, all in Track 2's `dev` target.

**Isolation.** Track 1 is untouched — different pipelines, different schemas.
All Track 2 data is generated by `src/bedoux/generator.py`, so no real data is
involved at any stage. Recovery is structural rather than procedural: Bronze is
a full deterministic recompute from a fixed seed, so re-running with normal
parameters reproduces the baseline exactly. There is no cleanup step to forget.

**Stage 1 — healthy baseline.** Run `bedoux_analytics_job` unmodified.

- Expect: all four tasks succeed, `gate_status` shows `gate_passed = true` for
  all three sources at roughly the generator's ~2% quarantine rate, and the
  three Gold tables populate.
- Record: each `gate_status` row, row counts for `<source>_clean` and
  `<source>_quarantine`, and the Gold row counts. This is the baseline that
  stage 2 must prove was preserved.

**Stage 2 — bad batch, withheld.** Re-run with the lead invalid rate raised
past the 10% threshold (say 30%).

- This needs a knob that does not exist yet: `bronze.py` hardcodes
  `generator.INVALID_RATE`. Add a pipeline `configuration` value (the same
  mechanism `bundle.sourcePath` already uses) read via `spark.conf.get` with
  the normal rate as default, so the demo changes a parameter rather than code.
  Specify it as part of the demo, not as a permanent behavior change.
- Expect: Bronze and Silver succeed; `leads_quarantine` fills; `gate_status`
  shows `gate_passed = false` for `leads`; **`bedoux_gate_task` fails**;
  `bedoux_gold_task` is skipped; the job run goes red.
- Record: the gate task's log showing which sources failed and why, and — the
  actual point of the chapter — **that the three Gold tables still hold stage
  1's row counts, unchanged**. A withheld refresh that silently emptied Gold
  would be a failure, not a success.
- Also worth recording: the whole-Gold tradeoff made visible.
  `gold_ogi_ops_health` does not depend on `leads`, and it is withheld anyway.

**Stage 3 — corrected batch, published.** Re-run with the parameter back to
normal.

- Expect: the gate passes, `bedoux_gold_task` runs, Gold refreshes, and the
  numbers match stage 1 exactly — same seed, same recompute.
- Record: Gold row counts equal to stage 1, and a green job run.

**Replay check.** Run stage 3 twice. Row counts must be identical across both,
demonstrating that reprocessing the same batch neither duplicates accepted rows
nor re-quarantines them differently. This is the only way to actually test the
idempotence the chapter currently only argues for.

**Evidence to capture,** sanitized: job run IDs and task outcomes, the gate
task log, `gate_status` contents per stage, and a row-count table across the
three stages. No credentials, no workspace URLs with tokens, no raw
screenshots containing account identifiers.

## 5. What this would and would not prove

Proves: the gate withholds on real data, Gold retains prior content, a
`notebook_task` with `base_parameters` runs on Free Edition serverless,
`{{job.start_time.iso_datetime}}` resolves and parses, `_computed_ts` compares
correctly across the timezone boundary, and replay is idempotent.

Does not prove: anything about security. A withheld refresh demonstrates a data
reliability control. It is not evidence that an attacker was stopped, that
sensitive data was protected, or that the platform is hardened. Those are
chapters 03 and 06, and they need their own runtime evidence.
