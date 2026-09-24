# Part 07 — The complete demonstration

Strategic theme: none new. This chapter runs the earlier ones in order
(see [README.md](../README.md)).

Status: **in progress on `series/07-full-demo`, not merged.** First step: a
local end-to-end demonstration, one command, fakes only, tied to the live
evidence already recorded. The user chose option 1: **no new live runs**.
Nothing in this chapter ran against Databricks or called a model; every
live fact below comes from runs recorded in chapters 02 and 03.

## Acceptance criteria, mapped before building

`roadmap.md`, chapter 07: "Run the same incident from a healthy dashboard
through detection, redaction, classification, investigation, approved
replay, and reconciliation. Link the retained chapter branches and exact
post snapshots from the series index. Acceptance: a 4–6 minute video,
reproducible scenario instructions, final architecture, evaluation report,
and documented limitations. Label cached model responses or edited waiting
periods. Verify every performance claim against a run."

**Acceptance criteria:**

| Criterion | State | Proof | Needs something live, or someone else |
| --- | --- | --- | --- |
| A 4–6 minute video | **Script drafted, not recorded** | "Final video: demo script (draft)," below. | Recording and publishing are the user's. |
| Reproducible scenario instructions | **Met locally** | One command, `uv run --locked python -m scripts.full_demo`, deterministic output; `tests/test_full_demo.py` checks its outcomes and that two runs print the same thing. The live half is reproducible from [live-verification.md](../live-verification.md), not rerun here. | Nothing for the local half. |
| Final architecture | **Not done** | The diagrams are the user's, edited by hand. "Where each step runs," below, is a text version of what the demo exercises. | The user. |
| Evaluation report | **Not done: a harness, no result** | Chapter 05's `routing.evaluate` and frozen held-out set exist. Their only numbers describe scripted fakes. | A real provider with frozen versions and a spend cap; not authorized. |
| Documented limitations | **Written** | "What's live and what's fake," "What this doesn't show," below, and [known-gaps.md](../known-gaps.md). | Nothing. |
| Label cached model responses or edited waiting periods | **Met, trivially** | No cached real-model responses exist. Every model answer is a scripted fake, labelled on screen in the video script. No waiting period is edited: the demo takes well under a second. | Recording the video may add edits; the script says to label them. |
| Verify every performance claim against a run | **Met, with no performance claims** | The script and doc make no latency, cost, or accuracy claims. Every count cites either the demo's output or a recorded live run. | Nothing. |

**Scope items (the roadmap's path):**

| Step | In the local demo | Live evidence already recorded |
| --- | --- | --- |
| Healthy dashboard | Not shown. The bundle has no dashboard resource. | Chapter 02's confirmed-good baseline: Gold's three tables and digests. |
| Detection | The gate refuses (step 1) | **Yes**, chapter 02's fault run and chapter 03's failing evidence row. |
| Redaction | **Not exercised.** This case holds no sensitive field. | No. Redaction is unit-tested (chapter 03), never live against a model. |
| Classification | Rules-only routing (step 2); fake models in step 8 | No. |
| Investigation | Fake model, three read-only tools over in-memory fixtures (steps 3–5) | No. |
| Approved replay | Fake executors over an in-memory store (steps 6–7) | **Partly**: chapter 02 replayed live, but with no approval step. |
| Reconciliation | Conservation in the gate rows; one copy per lead in the store | **Yes**, `conserved=true` on every chapter 02 run. |
| Link retained chapter branches and exact post snapshots from the series index | **Partly**. The seven chapter branches are listed below. No post is published and no tag exists, so there are no snapshots to link. | Publishing and tagging are the user's. |

## Run it

```
uv run --locked python -m scripts.full_demo
uv run --locked python scripts/full_demo.py
```

Both forms print identical output.

`scripts/full_demo.py` calls the project's own modules in `src/bedoux`,
unchanged. It writes its incident log to a temporary directory and deletes
it. It prints counts, fixed reason codes, citation paths and truncated
SHA-256 hashes. It never prints a raw record field or h07's text, and
nothing random: incident and approval ids are uuid4, so they aren't printed.
`tests/test_full_demo.py` asserts the outcomes below and checks the output
for raw fields and the instruction text.

The script lives in `scripts/`, outside the bundle's paths, so merging it
wouldn't trigger a deployment.

## The demo's output

Recorded from `series/07-full-demo` on 2026-09-24, Python via `uv run
--locked`, local machine. The output is deterministic; a second run prints
the same lines (`test_the_output_is_deterministic`).

```
1. publication gate (chapter 02)
   leads: 500 total, 336 accepted, 164 quarantined (32.8%), gate_passed=False, conserved=True
   web_events: 2000 total, 1954 accepted, 46 quarantined (2.3%), gate_passed=True, conserved=True
   ops_events: 365 total, 357 accepted, 8 quarantined (2.2%), gate_passed=True, conserved=True
   gate: REFUSED; failing sources: leads; 1 problem(s); Gold refresh withheld
2. routing (chapters 05-06), rules only: no model call
   label=data_quality action=runbook severe=True codes=gate_failed
3. incident (chapter 04)
   opened and fsynced before the first model call: True
   opening payload sha256 f82d72f287df
4. read-only tools (chapter 04), requested by the fake model
   read_gate_status: ran, payload sha256 38e0ce7efcaf
   read_quarantine_sample: ran, payload sha256 7e18228a2439
   read_evidence_log: ran, payload sha256 9a2bfe53a594
5. report: reported, 4 fake model calls, citations resolved:
   evidence.quarantine_rate
   evidence.conserved
   tool_results[0].result[0].gate_passed
   tool_results[1].result[0].lead_id
   tool_results[2].result[0].passed
   report sha256 2fcb7f7f0b2e
6. approvals, bound to incident + action + payload sha256 9a2bfe53a594
   before recovery: 336 accepted leads (fault batch)
7. recovery (chapter 04), executors act on local state only
   restore_lead_invalid_rate: executed (lead rate 0.3 -> 0.02)
   replay_batch: executed, inserted=161 updated=324 unchanged=5 quarantined=10
   same approval again: refused (approval_already_used), executor not called
   replay_batch, new approval: executed, inserted=0 updated=0 unchanged=490 quarantined=10
   after recovery: 497 accepted leads, at most 1 copy of each lead_id
   of those, 7 were accepted only in the fault batch and stay: a replay merges, it never removes (known limit)
8. refusal: h07's embedded instruction (chapter 06); every fake model says healthy
   rules_only: label=suspicious_instruction action=runbook codes=instruction_in_evidence
   rules_plus_reasoning: label=healthy action=human codes=instruction_in_evidence,severe_signal_not_dismissable
   rules_plus_classifier: label=healthy action=human codes=instruction_in_evidence,severe_signal_not_dismissable
9. refusal: prohibited action export_leads (chapter 06)
   as a tool: refused (prohibited_action)
   approval: refused (ValueError, nothing recorded)
   as a recovery, with a real approval id: refused (prohibited_action), executor calls: 0
incident log events: opened=1, outcome=1, recovery_approved=3, recovery_requested=2, recovery_result=3, recovery_started=3, tool_call=3
no real model, table, or workspace was touched; see the chapter 07 doc
```

Notes on reading it:

- **Order.** Routing (step 2) runs before the incident is opened (step
  3). That's safe for the ordering guarantee because rules-only routing
  calls no model: the first model call of the run is the investigation's,
  and the fake checks on that call that the `opened` event is already the
  only thing on disk. Routing a severe incident through a model first
  would break "saved before any model call", because `route()` doesn't
  open an incident. That's also why step 2's decision isn't in the audit
  record: `route()` records only when given an incident id, and none
  exists yet.
- **Approvals.** A person doesn't approve anything here. The script calls
  `approve_recovery` on a person's behalf, naming itself as the approver.
  The checks are the real ones: bound to this incident, this action, and
  the hash of the latest payload (`9a2bfe53a594`, the third tool call's),
  and each approval works once.
- **Recovery.** Three approvals, three executor calls: restore the lead
  rate, replay, and replay again under a fresh approval. The reused
  approval is refused and never reaches the executor. The second replay
  inserts and updates nothing.
- **497, not 490.** The store starts with the 336 leads the fault batch
  accepted. Seven of them are quarantined in the restored batch, and a
  replay merges rows; it never removes them. That's chapter 04's
  documented limit (`test_a_replay_never_removes_an_earlier_accepted_record`),
  shown here rather than hidden. It says nothing about the live pipeline,
  which recomputes Silver in full on every run.
- **h07.** Every fake model answers healthy at 0.99. No strategy
  dismisses. Rules-only gets the label right; the two model strategies
  keep the fooled label and send it to a person.
- **Export.** Refused by name on both paths, before the allowlist. Passing
  the replay's real approval id doesn't help, and no approval can be
  recorded for it.

## What's live and what's fake

No step of this chapter was run live. The table says which steps match
live evidence already recorded, and which exist only with fakes.

| Step | Backed by recorded live evidence? | Where |
| --- | --- | --- |
| 1. The gate refuses leads at 32.8%, conserved, and Gold is withheld | **Yes.** Same seeds, same rules, same counts: 500 / 336 / 164, `gate_passed=false`, `conserved=true`; web_events 2000 / 1954 / 46, ops_events 365 / 357 / 8. Live, Gold was skipped and its digests unchanged. | Chapter 02 fault run `330174171866992`, [chapter-02-evidence.md](../chapter-02-evidence.md), "Stage 3 — Fault". Chapter 03 failing run `180753859499836`, [chapter-03-evidence.md](../chapter-03-evidence.md), "Run 3". |
| The failing evidence row exists and can't be edited | **Yes** (not part of the local run; the local fixture is a synthetic stand-in for this row) | Run `180753859499836` wrote a `passed=false` row to `gate_evidence_log`, reason `leads: gate_passed is false (quarantine rate 32.8%)`. The negative test's `UPDATE` and `DELETE` against real rows both failed with `[DELTA_CANNOT_MODIFY_APPEND_ONLY]`, and the rows stayed identical. Same doc, "Phase B". Its retry also wrote a duplicate row (a known gap). |
| Restore, then replay without duplicates | **Partly.** Live: restore run `262274593519322`, then replay run `98756061776337`, identical Silver counts and Gold digests. That replay had **no approval step**; it was an operator rerunning the job. | [chapter-02-evidence.md](../chapter-02-evidence.md), "Stage 4" and "Stage 5". |
| 2. Rules-only routing flags it severe | No, fakes and local code only | Chapter 05 unit tests. |
| 3. Incident saved before the first model call | No. The model is a fake, and the log is a local file. | Chapter 04 unit tests. |
| 4. Read-only tools | No. The tools read in-memory fixtures, never the Databricks tables. | Chapter 04 unit tests. |
| 5. Cited report | No. The report is scripted. | Chapter 04 unit tests. |
| 6–7. Approval, approved restore and replay, reuse refused | No. The executors change a local variable and an in-memory store. | Chapter 04 unit tests. |
| 8. h07 can't dismiss | No. Fake models, a synthetic case. | Chapter 06 unit tests. |
| 9. Export refused | No. Nothing prohibited exists to call. | Chapter 06 unit tests. |

In one sentence: the data failure and its evidence are live; the agent
around them is not. **No real model has been called in this project.**

## Where each step runs

A text stand-in for the final architecture; the diagrams are the user's.

- **In Databricks (live, recorded earlier):** Bronze and Silver pipelines,
  `gate_status`, `bedoux_gate_task`'s gate and its append-only
  `gate_evidence_log`, and Gold withheld on failure.
- **In a local process (demonstrated only here, with fakes):** evidence
  gating and redaction (`model_call.prepare_payload`), routing, the
  incident log, tools, citations, approvals, recovery, and the boundaries.
- **Not built:** a real model provider, real tool readers against the
  tables, real recovery executors, and a dashboard.

## What this doesn't show

- Anything about a real model: what it would answer, how often it would be
  fooled, how long it would take, or what it would cost.
- That the local controls sit in front of real writes. The executors are
  local; no code path from this process reaches the workspace.
- Redaction in the end-to-end path: this incident carries no sensitive
  field. Chapter 03's unit tests and the chapter 04 gate cover it.
- The same code under Spark. The demo applies Silver's rules in pure
  Python (`quality.py`); the chapter 02 counts agree with the live run,
  which is the evidence that the two agree for this seed.
- The composed finale the roadmap's shared scenario describes: malformed
  leads, a missing campaign, a sensitive field, and an embedded
  instruction in *one* batch. Here they're separate cases.

## Branches readers can revisit

Retained chapter branches: `series/00-introduction`,
`series/01-know-your-platform`, `series/02-quality-gate`,
`series/03-protect-evidence`, `series/04-investigate-recover`,
`series/05-jev-routing`, `series/06-agent-boundaries`, and this chapter's
`series/07-full-demo`. No post tags exist; see
[branch-workflow.md](../branch-workflow.md)'s publication register.

## Final video: demo script (draft)

Draft only; not recorded, not published. Target about 5 minutes: about
450 words of narration, the rest reading output on screen. Follows writing.md's outline: inspiration
and business question; healthy dashboard and bad batch; quarantine and
publication gate; redacted evidence and investigation; approved replay and
reconciliation; measured evaluation and a limitation.

**Standing on-screen label, the whole video:** "Databricks steps: recorded
runs from chapters 02–03, not rerun. Agent steps: local code with scripted
fake models. No real model has been called."

**0:00–0:40 — The question.**
On screen: the series title, then the roadmap table.
Narration: "This series started from one question: when a campaign batch
goes bad, what stops it from reaching the numbers people read, and what
stops an AI helper from making it worse? Seven chapters built one answer,
one control at a time. This is all of them on one incident."

**0:40–1:30 — The bad batch, live (recorded).**
On screen: `chapter-02-evidence.md`, Stage 3, with run
`330174171866992`. Then the `gate_status` result: leads 500, 336 accepted,
164 quarantined, `gate_passed=false`, `conserved=true`. Label: "Recorded
live run, 2026-09-21. Not rerun for this video."
Narration: "We pushed the lead generator's invalid rate to 30 percent. The
gate refused: 32.8 percent quarantined against a 10 percent threshold.
Conserved is true, so this is a real rejection, not rows gone missing.
Gold didn't refresh; its digests didn't change." There's no dashboard in
this project, so say so: "No dashboard here; Gold's unchanged tables are
the healthy view."

**1:30–2:00 — The evidence can't be edited (recorded).**
On screen: `chapter-03-evidence.md`, Run 3's `passed=false` row, then
Phase B's `[DELTA_CANNOT_MODIFY_APPEND_ONLY]` error for `UPDATE` and
`DELETE`. Label: "Recorded live, run `180753859499836`."
Narration: "The failing run left a row in an append-only log. Updating or
deleting it failed. One honest wrinkle: the job's retry wrote the row
twice. Append-only stops edits, not duplicates."

**2:00–2:15 — Switch to local.**
On screen: a terminal running `uv run --locked python -m
scripts.full_demo`. Label: "From here on: local process, scripted fake
model."
Narration: "Everything after this runs on my machine. The model is a
script. No real model has ever been called in this project; I'll say that
again when it matters."

**2:15–3:15 — Routing, incident, investigation.**
On screen: output steps 1–5, one at a time.
Narration: "Same seeds, same rules in Python: the same 336 and 164.
Routing uses rules only and calls it severe. The incident is written and
fsynced before the first model call. The fake then asks for three tools,
all read-only, all on an allowlist, each result gated before it goes back.
Its report cites five fields, and each citation resolves in what it was
actually sent. The screen shows hashes, not data."

**3:15–4:05 — Approval and replay.**
On screen: steps 6–7.
Narration: "Recovery needs an approval tied to this incident, this action,
and the exact evidence reviewed. In this demo the script records it
standing in for a person; label it that way. Restore, replay, then reuse
the same approval: refused, the executor never runs. A fresh approval
replays again: nothing inserted, nothing updated. One copy of each lead.
And 497, not 490: seven leads accepted during the fault stay, because the
replay merges and never removes. That's a documented limit of this
stand-in. The live replay in chapter 02 had no approval step at all."

**4:05–4:45 — Two refusals.**
On screen: steps 8–9.
Narration: "Case h07 has an ops message telling the system to ignore its
instructions and mark the batch healthy. Every fake model agrees with it.
The two model strategies are fooled and keep the wrong label, healthy,
but they can't act on it: the case is severe, so it goes to a person
instead of being dismissed. And when the model asks to export leads, it's refused by
name, as a tool and as a recovery, even with a real approval id."
Don't show h07's text on screen; describe it.

**4:45–5:20 — Evaluation and the limit.**
On screen: this doc's "What's live and what's fake" table.
Narration: "There's no evaluation result to show. Chapter 05 built the
harness, but its only numbers come from fakes, so I'm not presenting them.
The data failure and its evidence are live. The agent around them isn't.
Next is a real provider, with pinned versions and a spend cap, and real
executors, each with its own approval."

**Replays and edits to label:** the Databricks screens are recorded
evidence, not a live run: label every one. If the terminal is re-recorded
or cut, say so. No waiting period exists to edit.

**Visual to suggest:** the "What's live and what's fake" table, full
screen, at the end. It's the one image that states the scope.

**Before recording:** confirm the demo prints the lines above on the
recorded commit, and cite that commit's SHA in the video description.
Don't show workspace URLs or IDs beyond the run IDs already in the
evidence docs.
