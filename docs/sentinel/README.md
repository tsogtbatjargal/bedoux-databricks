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
- **Integrated into `main`, not acceptance-complete**: chapter 03 ("Protect
  what matters") — pure-Python redaction/canary logic is implemented and
  unit-tested, but the roadmap's "a failed check prevents the external
  call" criterion is structurally blocked until chapter 04 builds a caller.
  See [chapters/03-protect-evidence.md](chapters/03-protect-evidence.md).
- **Integrated, not yet demonstrated live**: chapter 01 ("Know your
  platform") — the platform/threat map. See
  [chapters/01-know-your-platform.md](chapters/01-know-your-platform.md).
- **Planned**: chapters 04–07.

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
- [Known gaps](known-gaps.md): durable cross-chapter register of deferred,
  not-fixed gaps — testing boundaries, evidence durability, unexercised
  code paths.
- [Session handoff](handoff.md): where the next session should begin.
- [Chapter 00: The challenge](chapters/00-introduction.md): an unpublished launch post.
- [Chapter 01: Know your platform](chapters/01-know-your-platform.md): the platform/threat map.
- [Chapter 02: Defend before damage spreads](chapters/02-quality-gate.md): the publication gate, demonstrated live.
- [Chapter 03: Protect what matters](chapters/03-protect-evidence.md): redaction/canary logic, not acceptance-complete.

## Docs lifecycle

- **`handoff.md` is the single live handoff.** It gets overwritten in place
  at the end of each session, not archived — Git history already holds
  every prior version, so a separate snapshot file duplicates what `git log
  -p -- docs/sentinel/handoff.md` already gives you. An earlier session
  created a one-off `handoff-2026-09-22-archive.md` before this policy was
  written; it has been removed now that the policy is explicit, since
  keeping it around would read as a pattern to repeat rather than the
  exception it was.
- **`claude-implementation.md` is a dated, expiring working brief, not
  reference documentation.** It says so at its own top. Re-derive chapter
  04's actual first increment from the current codebase when that chapter
  starts, rather than trusting that file's specifics — then delete or
  archive it.

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

**Neither diagram shows chapter 03's evidence-redaction boundary.** That is
deliberate, not an oversight: `src/bedoux/evidence.py` is not wired into
the job or any pipeline task yet (see
[chapters/03-protect-evidence.md](chapters/03-protect-evidence.md)), so it
has no architectural edge to draw. Add it to both diagrams once chapter 04
gives it a real call site — not before.

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
