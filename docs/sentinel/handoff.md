# Session handoff

Read this for current state; follow links only when the task needs them.
This records context, not authority to merge, deploy, run jobs, change secrets,
bind resources, publish, or spend on model APIs. Inspect Git first.

## Current state

- Chapter 02 is integrated, demonstrated live, and review-closed. Its post
  is drafted, not published. See [evidence](chapter-02-evidence.md) and
  [chapter doc](chapters/02-quality-gate.md).
- Chapter 03 is integrated (PR #6, merge `569c03d`), **not acceptance-complete**.
  `src/bedoux/evidence.py` implements recursive redaction, sensitive-copy checks,
  and canary checks. No production caller or model transport exists. Tests
  establish fixture behavior, not prevention of a real external call.
  See [acceptance mapping](chapters/03-protect-evidence.md#roadmap-acceptance-mapping).
- Last recorded workspace verification: fourth CI deployment, normal
  `bedoux_lead_invalid_rate=0.02`, unchanged pipeline IDs, one analytics job,
  Bronze → Silver → gate → Gold, unchanged Gold digests. This session did
  not recheck the workspace. Prior checks and review history are preserved in
  [the archived handoff](handoff-2026-09-22-archive.md).
- Chapters 04–07 remain planned. Jev is optional; no provider/budget has been
  selected for runtime calls. AWS remains deferred.

## Workflow preparation — 2026-09-22

The user requested project analysis and help making Claude implementation
token-efficient, including evaluating Jev. Work is on local branch
`series/00-claude-efficiency`, based on `main` at `25e1784`; inspect actual Git
state rather than assuming the branch or uncommitted state remains unchanged.

- Added [Claude implementation brief](claude-implementation.md): bounded next
  task, completion sequence, context discipline, and Jev evaluation criteria.
- Kept existing chapter/story skills; no extra skill or routing hook needed yet.
- Shortened this startup file; preserved the previous handoff in the archive
  apart from its archival heading and navigation link.
- Added Claude compaction guidance and linked the brief from agent setup.
- Code inspection found a future logging hazard: `evaluate_evidence_gate`
  interpolates leaked values into its returned problem strings. Nothing calls
  it in production yet. The next runtime increment must use safe reason codes
  and test logs, reports, and exceptions as well as outbound requests.
- No runtime code, dependency, credential, model routing, or workspace changes.
  Documentation remains uncommitted; no push or paid model call occurred.

## Checks and remaining limits

On 2026-09-22, local Linux checkout at `25e1784`, locked project environment:
`uv sync --locked` succeeded; `uv run --locked python -m pytest -q` reported
**121 passed in 0.11s**, using repository synthetic fixtures. Claude Code
`2.1.263` is installed; account/billing access was not inspected.

Documentation checks: `git diff --check` passed; 16 local file links resolved;
the archived handoff body matched `HEAD:docs/sentinel/handoff.md` exactly.
A synthetic copied-secret check reproduced the diagnostic-string hazard without
printing the value. No live service was involved.

These tests do not execute Spark or prove IAM, live replay, or provider behavior.
Remaining [known gaps](known-gaps.md): manual durable incident evidence,
client/campaign dedup ties, unexercised conservation failure paths, and CI
credential expiry. Redaction also misses unrecognized freeform sensitive text,
short copied strings, and non-string copied values; it is not general DLP.

## Architecture SVG update — 2026-09-22

Updated `docs/architecture-context.svg` for the user's introduction image.
The user's final clarification was to restore the detailed diagram and remove
only the TPC-H section. The SVG retains GitHub Actions CI/CD, Asset Bundle,
Unity Catalog, full Bedoux pipeline/schema labels, the notebook publication
gate, SQL Warehouse and Genie. The layout closes the gap left by TPC-H.
Underlying pipelines/resources are unchanged. The direct-Gold bypass limitation
and planned agent/routing/recovery status remain explicit. No workspace IDs
appear. The separate `.drawio` remains the broader two-track map.

Checked against `resources/bedoux_jobs.yml`, `quality.py`, `gate_check.py` and
the Track 2 contract. SVG XML/unique IDs/gate edges and `git diff --check` passed.
Rendered with ImageMagick and inspected visually. The SVG is 900×800; the
refreshed 1800×1600 PNG export is in the user's
external content folder at
`/var/home/tsogtb/src/github.com/bedoux-tech/bedoux-sentinel-content/2026-09-22/architecture-context.png`.
No runtime files changed or live jobs ran. SVG and handoff remain uncommitted
alongside the pre-existing workflow edits. Next for the post: author review of
the updated image; no publication or remote update has occurred.

## Exact next useful task

Chapter 04 is deferred; [the implementation brief](claude-implementation.md)
stays as a prepared plan, not an active task -- do not act on its invocation
without separate authorization. Two things are authorized and outstanding
first:

1. **Fix the leak `claude-implementation.md`'s assessment found**:
   `evaluate_evidence_gate`'s sensitive-copy problem string embeds the
   leaked value verbatim (`src/bedoux/evidence.py`) -- a gate that blocks a
   packet and then hands the secret to whoever reads the rejection defeats
   its own purpose. Fix on a new branch from `main`; this touches
   `src/**`, so merging deploys.
2. **Align the docs with what has actually shipped**: `live-verification.md`
   still reads as pre-chapter-02, `README.md`'s "planned, not current
   deployment" framing predates chapter 02's integration, `known-gaps.md`
   has zero chapter 03 entries, and chapter 01 has no post draft. Docs-only,
   no deploy.

No API account is needed for either. Chapter 04's first increment (guarded
provider boundary, offline incident persistence, failure-path tests) waits
until it is explicitly authorized. Publishing chapter 02 remains separate
and unrequested.
