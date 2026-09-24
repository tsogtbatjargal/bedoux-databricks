# The Art of Data Defense

Bedoux Sentinel is the next part of `bedoux-databricks`: a small project about
protecting a fictional marketing lakehouse and investigating incidents with agents.
The existing medallion pipelines are the starting point.

**Build status, current as of this writing** (full detail and acceptance
criteria in [roadmap.md](roadmap.md); build status is tracked separately
from publication status, since a chapter can be fully implemented and
deployed with its post still unpublished):

- **Deployed and demonstrated live**, not just implemented: chapter 02
  ("Defend before damage spreads") — five full job runs in `dev`, a complete
  fault → restore → replay sequence, review-closed against two follow-on
  findings. See [chapters/02-quality-gate.md](chapters/02-quality-gate.md)
  and the durable per-stage record in
  [chapter-02-evidence.md](chapter-02-evidence.md).
- **Integrated into `main`, acceptance-complete at code level, not
  demonstrated live against a model**: chapter 03 ("Protect
  what matters") — pure-Python redaction/canary logic is implemented and
  unit-tested, and the append-only evidence log built on top of it
  (`evidence_log.py`) is deployed at `7856b78` and confirmed live across
  four `dev` runs: a row written every run matching `gate_status`
  (including a failing run's row, with its first-ever non-empty
  `problems`), `delta.appendOnly` confirmed genuinely set, and a negative
  test confirming `UPDATE`/`DELETE` are actually rejected against real
  rows. A predicted limitation was confirmed in that testing: a retried
  failing run writes a duplicate evidence row (see `known-gaps.md`). The
  last criterion, "a failed check prevents the external call", is met as
  implemented and unit-tested: chapter 04's `model_call.py` (merged)
  returns before calling its provider when the gate fails. Its provider is
  a test fake, deliberately — no evidence has left the process, and a live
  proof would need a real provider. See
  [chapters/03-protect-evidence.md](chapters/03-protect-evidence.md) and
  [chapter-03-evidence.md](chapter-03-evidence.md).
- **Integrated, not yet demonstrated live**: chapter 01 ("Know your
  platform") — the platform/threat map. See
  [chapters/01-know-your-platform.md](chapters/01-know-your-platform.md).
- **Integrated into `main`, acceptance-complete at code level, not
  demonstrated live**: chapter 04 ("Investigate and recover"). It has
  five increments: a guarded model-call path, a local incident log,
  report citations, read-only tools with recovery refused in code, and
  approved recovery with duplicate-free replay. All run against a fake
  provider and synthetic fixtures. The before/after business metric and
  the live run are deliberately deferred together, because both need a
  real provider. No real model has been called, and nothing has run
  against the real tables. See
  [chapters/04-investigate-recover.md](chapters/04-investigate-recover.md).
- **Integrated into `main`, acceptance-complete at code level, not
  demonstrated live**: chapter 05 ("Spend intelligence carefully"). Rules,
  a cheap classifier, and selective escalation, all through chapter 04's
  gate, with fake models only, plus a frozen held-out set and a scoring
  harness. The chapter's central result is a measurement, so closing it
  at code level means the harness exists but the result doesn't: the
  live three-way comparison is deliberately deferred with the other
  provider work. See
  [chapters/05-spend-intelligence.md](chapters/05-spend-intelligence.md).
- **In progress**: chapter 06 ("Establish rules of command"). The first
  step is integrated: instructions inside evidence can't dismiss an
  incident, add a tool, approve a recovery, or clear a failed gate. A
  second step, not merged, adds an audit record of routing decisions and
  a prohibited-action list. Fake providers only. See
  [chapters/06-rules-of-command.md](chapters/06-rules-of-command.md).
- **Planned**: chapter 07.

The story follows one campaign batch through validation, evidence handling,
investigation, and recovery. Each chapter adds something a reader can reproduce.
The final video brings those pieces together.

## Start here

- [Roadmap](roadmap.md): chapter scope, completion criteria, and current status.
- [Branch workflow](branch-workflow.md): retained remote branches, local cleanup, and post tags.
- [Local development](../development.md): isolated uv environment and dependency updates.
- [Agent setup](agent-setup.md): Codex, Claude Code, and optional Jev development.
- [Writing guide](writing.md): voice, evidence, and the final video outline.
- [Live verification](live-verification.md): credential setup, what deploys
  automatically, and the demonstration procedure chapter 02 used (and a
  future chapter will reuse).
- [Chapter 02 evidence](chapter-02-evidence.md): the durable per-stage
  record of the live demonstration — run IDs, `gate_status` rows, Gold
  digests.
- [Chapter 03 evidence](chapter-03-evidence.md): the durable per-run
  record of the evidence log's live demonstration — run IDs,
  `gate_evidence_log` row content, and the confirmed `delta.appendOnly`
  table property.
- [Known gaps](known-gaps.md): durable cross-chapter register of deferred,
  not-fixed gaps — testing boundaries, evidence durability, unexercised
  code paths.
- [Session handoff](handoff.md): where the next session should begin.
- [Chapter 00: The challenge](chapters/00-introduction.md): an unpublished launch post.
- [Chapter 01: Know your platform](chapters/01-know-your-platform.md): the platform/threat map.
- [Chapter 02: Defend before damage spreads](chapters/02-quality-gate.md): the publication gate, demonstrated live.
- [Chapter 03: Protect what matters](chapters/03-protect-evidence.md): redaction/canary logic and the append-only evidence log, deployed and confirmed live including a negative mutation test; acceptance-complete at code level.
- [Chapter 04: Investigate and recover](chapters/04-investigate-recover.md): guarded model call, incident log, cited reports, read-only tools, approved recovery, and replay — acceptance-complete at code level, fake provider only, not demonstrated live.
- [Chapter 05: Spend intelligence carefully](chapters/05-spend-intelligence.md): routing with fake models through chapter 04's gate, a frozen held-out set, and a scoring harness — acceptance-complete at code level; the live comparison is deferred.
- [Chapter 06: Establish rules of command](chapters/06-rules-of-command.md): in progress — instructions inside evidence are data, never commands.

## Docs lifecycle

- **`handoff.md` is the single live handoff.** It gets overwritten in place
  at the end of each session, not archived — Git history already holds
  every prior version, so a separate snapshot file duplicates what `git log
  -p -- docs/sentinel/handoff.md` already gives you. An earlier session
  created a one-off `handoff-2026-09-22-archive.md` before this policy was
  written; it has been removed now that the policy is explicit, since
  keeping it around would read as a pattern to repeat rather than the
  exception it was.
- **Dated working briefs expire.** `claude-implementation.md` was one: a
  snapshot written to start chapter 04. It was deleted when chapter 05
  started, having served its purpose. Its Jev guidance was carried into
  [chapters/05-spend-intelligence.md](chapters/05-spend-intelligence.md),
  and the full text is in Git history. A future brief should say at its
  top that it expires, and should be deleted rather than kept current.

## Inspiration

[IBM Technology's video](https://www.youtube.com/watch?v=kjoQPn--F7A) connects eight
themes from Sun Tzu's *The Art of War* to cybersecurity. This project adapts those
themes to data contracts, publication gates, evidence, and agent permissions.
The controls are modern engineering choices, not historical prescriptions.

The book is traditionally attributed to Sun Tzu. "Roughly 2,500 years old" is an
introductory framing; its authorship and dating are debated. See the
[Library of Congress description](https://www.loc.gov/resource/gdcwdl.wdl_11410_001/?sp=10).

[Ray Amjad's Jev video](https://www.youtube.com/watch?v=ScvXFi4MUSc) inspired the
experiment with inexpensive classification and selective escalation. We will
measure whether that extra step helps on our incidents.

| Strategic theme | Where it appears |
| --- | --- |
| Know yourself and the threat | Part 01: assets, trust boundaries, incident scenarios |
| Prevent damage early | Part 02: validation and publication gates |
| Use deception | Part 03: synthetic canary marker; optional AWS decoy later |
| Respond and adapt | Part 04: investigation and controlled recovery |
| Prioritize critical assets | Parts 01 and 03: business impact and sensitive evidence |
| Maintain visibility and separation | Parts 01 and 06: dependency map, audit trail, permissions |
| Establish responsibility | Part 06: ownership, approvals, incident review |
| Use resources carefully | Part 05: measured Jev routing and escalation |

## Diagrams

Two hand-maintained diagrams exist, and they are not duplicates of each
other despite both depicting parts of this system — checked directly:
`architecture-context.svg` embeds no `mxfile` data, so it is not exported
from the `.drawio` file; each is authored and updated independently.

- **`../architecture.drawio`** is the canonical technical architecture
  source, documented in [`../architecture.md`](../architecture.md). It
  covers **both** tracks (Track 1 TPC-H and Track 2 Bedoux) at full
  technical detail — every pipeline, table, job, and Free Edition
  constraint. Edit it in draw.io desktop or diagrams.net; regenerate any
  exported PNG per `architecture.md`'s instructions. This is the source of
  truth for the platform's actual architecture.
- **`../architecture-context.svg`** is a separate, deliberately narrower
  illustration: Track 2 (Bedoux) only, styled as a single system-context
  image for external use (the chapter 00 introduction post), not an
  attempt at technical completeness. It is hand-authored SVG, not derived
  from the `.drawio` file, and is updated by hand when the introduction
  narrative changes — most recently to drop a stray TPC-H reference and
  restore full Bedoux pipeline/gate detail. It currently has no rendered
  PNG checked into this repo; an exported copy lives in the author's
  external content folder for the post itself.

**Both diagrams now show chapter 03's evidence-redaction boundary.**
`src/bedoux/evidence.py` has a real call site — `gate_check.py` calls into
it via `evidence_log.py` as a sub-step inside `bedoux_gate_task`, deployed
at `7856b78` and run live twice (see
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md)).
`architecture.drawio`'s `gate2` cell names that sub-step in its label
rather than drawing it as a peer box, matching `architecture.md`'s
argument that it's a sub-step, not a new task.
`architecture-context.svg`'s `bedoux-publication-gate` group and its
accessibility `<desc>` do the same at that diagram's coarser detail.
Neither diagram draws or implies a model-call arrow. Chapter 04's
`model_call.py` is a call site, but its only provider is a test fake and
nothing in the job calls it, so there is still no model call to draw.

## Scope

Start with Databricks Free Edition, synthetic fixtures, and a local investigation
service. Keep AWS as an extension until required storage, identity, and access
features are verified. Track 1 remains the existing TPC-H demonstration.

Data defects and security incidents are different. A rejected row demonstrates
validation; it does not establish that an attack happened. A synthetic marker
blocked in a model payload proves that specific boundary check, not protection
against every way data might leave the platform.

The [current Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
must be checked before designing around external storage or enterprise security.
All implementation and publication states are tracked in the roadmap.
