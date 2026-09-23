# Architecture

Two tracks share one Databricks Asset Bundle, one CI/CD path, and one Genie/BI
layer. Diagram source: [`architecture.drawio`](architecture.drawio) (open in
[draw.io desktop](https://github.com/jgraph/drawio-desktop/releases) or
[diagrams.net](https://app.diagrams.net/) to view/export — no rendered PNG is
checked in yet since this machine has no draw.io desktop install to export one;
see the note at the bottom).

```
GitHub Actions CI/CD
  uv / pytest (every PR and main push)
  bundle changes -> validate -> deploy (main only)
  (manual dispatch: validate; opt in to deploy and optionally run the job)
        |                                   |
        v                                   v
 Track 1: TPC-H Medallion           Track 2: Bedoux Ops & Marketing
 (classic DE benchmark)             (brand-tied, fictional synthetic data)

 bronze_pipeline                    bedoux_bronze_pipeline
 workspace.bronze                   workspace.bedoux_bronze
 reads samples.tpch (8 tables)      seeded synthetic generator (5 entities)
        |                                   |
        v                                   v
 silver_pipeline                    bedoux_silver_pipeline
 workspace.silver                   workspace.bedoux_silver
 Auto CDC + DQ expectations         DQ expectations (drops ~2% invalid rows)
        |                                   |
        |                                   v
        |                          bedoux_gate_task (notebook, not a pipeline)
        |                          reads gate_status, fails the run before
        |                          Gold if any required source is missing,
        |                          null, stale, or over the quarantine-rate
        |                          threshold -- see "The publication gate"
        |                                   |
        v                                   v
 gold_pipeline                      bedoux_gold_pipeline
 workspace.gold (3 tables)          workspace.bedoux_gold (3 tables)

 orchestrated by                    orchestrated by
 tpch_medallion_pipeline_job        bedoux_analytics_job
 (sequential, manual trigger)       (sequential, manual/workflow_dispatch)
        \                                   /
         \                                 /
          v                               v
              Genie / AI-BI
     natural-language queries over both Gold layers
   shared 2X-Small SQL warehouse (Free Edition limit)
```

## The publication gate (Track 2 only)

Track 1's job is a plain three-task chain: `bronze_task` → `silver_task` →
`gold_task`, each a pipeline task. Track 2's `bedoux_analytics_job` has a
fourth task in between: `bedoux_gate_task`, a **notebook task**
(`src/bedoux/gate_check.py`), not a pipeline. It runs after
`bedoux_silver_task` and before `bedoux_gold_task`, reads the
`gate_status` table Silver just wrote, and raises if any required source
(`leads`, `web_events`, `ops_events`) is missing, has a null/duplicate
`gate_status` row, is stale relative to the run's start time, or has
`gate_passed`/`conserved` not strictly true. Raising fails the task, which
stops `bedoux_gold_task` from ever starting — Gold keeps its last published
content instead of refreshing from a bad batch.

This is deliberately **not** logic inside a Gold dataset function: DLT
dataset functions are declarative, and the gate needs driver-side actions
(`.collect()`, reading a table outside the pipeline currently being
defined) that aren't legal there. Putting the check in an ordinary
imperative notebook task, ahead of the Gold pipeline, is what makes
"withhold this refresh" actually enforceable. See
[`contracts-bedoux.md`](contracts-bedoux.md) and
[`sentinel/chapters/02-quality-gate.md`](sentinel/chapters/02-quality-gate.md)
for the full design and its live demonstration.

**Inside `bedoux_gate_task`, not shown as its own box:** `src/bedoux/evidence.py`
(sensitive-field redaction and canary detection, chapter 03) now has a real
call site. `gate_check.py` imports `evidence_log`, which calls
`evaluate_evidence_gate` and `redact_evidence_packet` before appending a
row to `workspace.bedoux_silver.gate_evidence_log` — deployed at `7856b78`
and run live twice. This guards a durable Delta write, not a network
egress, so it does **not** close the roadmap's "a failed check prevents
the external call" criterion, which names a model-API call; no such call
site exists anywhere in this project yet. It is omitted as a separate box
in the diagram above because it's a sub-step inside `bedoux_gate_task`,
not a new task — the diagram update to show that sub-step is still
outstanding, tracked separately from this correction. See
[`sentinel/chapters/03-protect-evidence.md`](sentinel/chapters/03-protect-evidence.md)
for what it does and doesn't close.

## Why it's shaped this way

**Two tracks, one bundle.** Track 1 (TPC-H) is the classic data-engineering
benchmark, done with real rigor (contracts-first, Auto CDC on genuinely
incremental dimensions, DLT expectations). Track 2 (Bedoux) applies the same
contracts-first medallion discipline to an original, brand-tied domain, and
deliberately *skips* CDC where it wouldn't fit (see
[`contracts-bedoux.md`](contracts-bedoux.md)) rather than cargo-culting the
Track 1 pattern everywhere. Track 1 also stays for that comparison point
itself — see README.md's "Why two tracks" for the decision to keep it.

**Both tracks feed one Genie space set-up**, so the portfolio has a natural
BI/self-serve-analytics story on top of the pipeline engineering, not just
pipeline code — see [`genie.md`](genie.md).

**Databricks Free Edition constraints directly shaped several decisions:**
- One SQL warehouse, fixed at 2X-Small — both tracks' Gold layers share it via
  Genie rather than provisioning separate warehouses.
- Max 5 concurrent job tasks and one active Lakeflow pipeline per pipeline type
  — both jobs are strictly sequential internally and are never triggered to run
  concurrently with each other.
- No account console / service principals — CI/CD authenticates with a personal
  access token stored as a GitHub Actions secret. In a paid workspace this would
  be OIDC federation to a service principal instead; that trade-off is called
  out explicitly rather than glossed over.
- No auto-schedule on either job — every run is a manual trigger or a
  `workflow_dispatch` button, to avoid tripping the quota-based shutdown Free
  Edition applies when compute usage is exceeded.
- Non-commercial use only — Track 2's client/campaign/lead data is clearly
  fictional and synthetic, never Bedoux's real business data.

## Regenerating the diagram

```bash
# View or edit
open docs/architecture.drawio   # or drag into https://app.diagrams.net/

# Export to PNG/SVG (requires draw.io desktop installed locally)
drawio -x -f png -e -s 2 -o docs/architecture.drawio.png docs/architecture.drawio
```
