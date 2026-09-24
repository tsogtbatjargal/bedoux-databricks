# The Art of Data Defense

Bedoux Sentinel is the next part of `bedoux-databricks`: a small project about
protecting a fictional marketing lakehouse and investigating incidents with agents.
The existing medallion pipelines are the starting point.

**Build status, current as of this writing** (full detail and acceptance
criteria in [roadmap.md](roadmap.md); build status is tracked separately
from editorial publication, which is tracked in the separate content workspace):

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
- **Integrated into `main`, acceptance-complete at code level, not
  demonstrated live**: chapter 06 ("Establish rules of command").
  Instructions inside evidence can't dismiss an incident, add a tool,
  approve a recovery, or clear a failed gate, because of where those
  decisions are made; the text filter is easy to evade and says so. Plus
  an audit record of routing decisions, a prohibited-action rule, and an
  honest failure analysis. Fake providers only. See
  [chapters/06-rules-of-command.md](chapters/06-rules-of-command.md).
- **Integrated into `main` at code level, not demonstrated live**: chapter
  07 ("The complete demonstration").
  One command runs chapter 02's fault case through every control from
  chapters 02–06 locally, with fake models, and the doc says which steps
  match live runs already recorded. No new live runs, by the user's choice.
  Video narration is maintained in the content workspace. See
  [chapters/07-full-demo.md](chapters/07-full-demo.md).

The story follows one campaign batch through validation, evidence handling,
investigation, and recovery. Each chapter adds something a reader can reproduce.
The final video brings those pieces together.

## Start here

- [Roadmap](roadmap.md): chapter scope, completion criteria, and current status.
- [Branch workflow](branch-workflow.md): retained remote branches, local cleanup, and post tags.
- [Local development](../development.md): isolated uv environment and dependency updates.
- [Agent setup](agent-setup.md): Codex, Claude Code, and optional Jev development.
- [Repository scope](repository-scope.md): technical files, shared agent setup and the separate editorial workspace.
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
- [Chapter 00: Shared development setup](chapters/00-introduction.md): technical instructions, skills and workflow.
- [Chapter 01: Know your platform](chapters/01-know-your-platform.md): the platform/threat map.
- [Chapter 02: Defend before damage spreads](chapters/02-quality-gate.md): the publication gate, demonstrated live.
- [Chapter 03: Protect what matters](chapters/03-protect-evidence.md): redaction/canary logic and the append-only evidence log, deployed and confirmed live including a negative mutation test; acceptance-complete at code level.
- [Chapter 04: Investigate and recover](chapters/04-investigate-recover.md): guarded model call, incident log, cited reports, read-only tools, approved recovery, and replay — acceptance-complete at code level, fake provider only, not demonstrated live.
- [Chapter 05: Spend intelligence carefully](chapters/05-spend-intelligence.md): routing with fake models through chapter 04's gate, a frozen held-out set, and a scoring harness — acceptance-complete at code level; the live comparison is deferred.
- [Chapter 06: Establish rules of command](chapters/06-rules-of-command.md): instructions inside evidence are data, never commands; audit record, prohibited actions, and a failure analysis — acceptance-complete at code level, fake providers only.
- [Chapter 07: The complete demonstration](chapters/07-full-demo.md): one local command runs the fault case end to end with fakes; which steps match recorded live evidence; narration maintained in the content workspace — integrated at code level, fake models only.

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

## Technical architecture

[architecture.drawio](../architecture.drawio) is the technical source covering
both tracks, pipelines, tables, jobs and platform constraints. Its editing and
export workflow is documented in [architecture.md](../architecture.md).

The separate introduction illustration, `architecture-context.svg`, moved to
`assets/` in the content workspace. It was hand-authored, not an export of
the technical diagram. Editorial graphics and book/video inspiration belong
there; see [repository scope](repository-scope.md).

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
The roadmap tracks implementation; the content workspace tracks publication.
