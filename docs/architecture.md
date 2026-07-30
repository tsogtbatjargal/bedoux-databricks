# Architecture

Two tracks share one Databricks Asset Bundle, one CI/CD path, and one Genie/BI
layer. Diagram source: [`architecture.drawio`](architecture.drawio) (open in
[draw.io desktop](https://github.com/jgraph/drawio-desktop/releases) or
[diagrams.net](https://app.diagrams.net/) to view/export — no rendered PNG is
checked in yet since this machine has no draw.io desktop install to export one;
see the note at the bottom).

```
GitHub Actions CI/CD
  pytest -> databricks bundle validate -> databricks bundle deploy
  (workflow_dispatch also offers: run the job)
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

## Why it's shaped this way

**Two tracks, one bundle.** Track 1 (TPC-H) is the classic data-engineering
benchmark, done with real rigor (contracts-first, Auto CDC on genuinely
incremental dimensions, DLT expectations). Track 2 (Bedoux) applies the same
contracts-first medallion discipline to an original, brand-tied domain, and
deliberately *skips* CDC where it wouldn't fit (see
[`contracts-bedoux.md`](contracts-bedoux.md)) rather than cargo-culting the
Track 1 pattern everywhere.

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
