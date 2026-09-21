# Session handoff

Updated: 2026-09-21, mid-session on chapter 01. Verify the checkout before
working; this page records context, not permission for external actions.

## Current state

- On `series/01-know-your-platform`, created from `main` at `66454c2` (verify
  the actual current `main` tip with `git rev-parse main`; do not trust a SHA
  recorded here — see the chapter 00 history note below for why).
- Local commits on this branch, none pushed:
  - `2e1f81d` — fixed two stale `main` SHA references in this file that a
    prior session's direct docs pushes had made stale.
  - `f5ddfc7` — added `docs/sentinel/chapters/01-know-your-platform.md` (the
    platform map, trust boundaries, three incident scenarios, one normal
    control, and a capability-check table); fixed two discrepancies in
    `docs/contracts-bedoux.md` (Bronze's "append-only" vs. "full recompute"
    self-contradiction, and Silver's "streaming tables" claim vs. its actual
    batch `@dlt.table` implementation); marked chapter 00 "Integrated into
    main" and chapter 01 "In progress" in `docs/sentinel/roadmap.md`'s build
    status column.
- Working tree clean. Not pushed, no PR, nothing merged, deployed, tagged, or
  posted this session.
- `uv sync --locked` and `uv run --locked python -m pytest -q` both pass (17
  passed) — no Python/pipeline code changed this session, docs only.

## Chapter 01 scope — status against acceptance criteria

All four required elements from `docs/sentinel/roadmap.md`'s chapter 01
acceptance are done locally; see
[`chapters/01-know-your-platform.md`](chapters/01-know-your-platform.md) for
the full content:

1. **Architecture/threat map distinguishing existing vs. planned parts** —
   done. Every row in the platform map cites the source file it was verified
   against (`src/bedoux/*.py`, `resources/bedoux_*.yml`, `databricks.yml`).
2. **Three scenario inputs + expected behavior, explicit** — done: malformed
   lead batch, duplicate leads, missing campaign reference, plus a normal
   control. Chosen to match chapter 02's stated scope
   ("malformed values, duplicate leads, and missing campaign references") so
   chapter 02 can build directly against them. The other two scenarios from
   the roadmap's shared set (unexpected sensitive field; instruction embedded
   in an ops message) are out of scope here — reserved for chapters 03 and
   06/07 respectively. Note: `ops_events` currently has no free-text field at
   all, so the ops-message scenario needs a schema addition before chapter
   06/07 can exercise it — flagged, not built.
3. **Capability checks recorded as verified/unavailable/untested** — done, see
   the table at the end of the chapter doc. Everything requiring live
   Databricks access (`bundle validate`, a live pipeline run, Genie queries)
   is **unavailable** in this environment: no `DATABRICKS_HOST`/
   `DATABRICKS_TOKEN`, no `~/.databrickscfg`, and the `databricks` CLI is not
   installed locally. This is an environment limit, not a choice — a session
   with workspace credentials should record the live baseline.
4. **Track 2 contract contradictions corrected** — done, both found while
   writing the platform map (not the ones originally guessed at): Bronze's
   opening line called itself "append-only" while its own rules three lines
   down said "full recompute... not append-only"; Silver called
   `leads`/`web_events`/`ops_events` "streaming tables" though `silver.py`
   implements them as batch-reading `@dlt.table`s (that phrase was inherited
   verbatim from Track 1's contract, where Bronze genuinely is append-only).
   No pipeline code changed — only the contract text, to match what
   `src/bedoux` already does.

Nothing in this chapter's scope remains undone locally. What's left is
integration (push/PR/merge), which was not authorized this session.

## Decisions to preserve

Build **Bedoux Sentinel** inside this repo, extending Track 2 with fictional data.
The series is **The Art of Data Defense**: introduction, six working chapters,
and a full demo. Use concrete, natural writing with measured evidence.

The user's latest branch preference: **keep remote chapter branches and stable
post tags; remove merged local chapter branches once their remote copy and
integration are verified.** See [branch workflow](branch-workflow.md) for exact
checks. Chapter 00 followed this policy: its local branch was removed after
verification, its remote branch and `main` remain.

Codex or Claude Code can implement; a separate session can review. Jev remains
optional and uninstalled. No runtime provider, API budget, AWS budget, or
publication date has been chosen. No Sentinel runtime exists yet — chapter 01
is still a mapping/documentation exercise, not new pipeline behavior.

## Chapter 00 — integration history (compressed)

Full session-by-session detail lived here before and is still in Git history
(`git log -- docs/sentinel/handoff.md`) if needed; compressed to the essentials
that matter going forward, matching the precedent set by the cleanup session
that did the same thing to the pre-chapter-00 history.

- Prepared on `series/00-introduction` across commits `bfd6fdd`, `b9250aa`,
  `a2231b7`, `04ded3a`, `0988d88`, `ea72679` (the last pinned
  `databricks/setup-cli` to a commit SHA and confirmed the `dorny/paths-filter`
  and `astral-sh/setup-uv` pins resolve to their intended tags via the GitHub
  API).
- Pushed, opened PR #1, confirmed `deleteBranchOnMerge` was already `false`,
  observed CI on the PR (`Unit tests` success, workspace jobs skipped — no
  bundle path changed), merged with a merge commit (`877e8d3`, no branch
  deletion), observed CI on the resulting `main` push (same no-deploy
  pattern), then ran every check in
  [branch workflow](branch-workflow.md)'s local-cleanup section before
  deleting the local branch. The remote branch
  (`series/00-introduction`) is retained at `ea72679`.
- Two further docs-only commits landed directly on `main` after the merge
  (`6be715b`, `66454c2`), each confirmed to run tests and skip workspace jobs.
  This is why "current state" sections in this file now defer to
  `git rev-parse main` instead of hardcoding a SHA — hardcoded SHAs here had
  already gone stale twice.

## Verification and limits (chapter 00 preparation)

- `mise exec -- uv run --locked python -m pytest -q`: 17 passed, confirmed
  independently by two separate sessions (interpreter CPython 3.11.16,
  `.venv` in this checkout both times).
- `uv lock --check`, `actionlint .github/workflows/ci.yml`, and a documentation
  check (Markdown files + relative links, TOML parse, `git diff --check`) all
  passed, also confirmed independently by two sessions.
- Local CI policy evaluation (path-filter conditions, dispatch flag
  combinations, deployment gating) was evaluated from the YAML and with Node,
  not by an actual GitHub Actions run — that only happened during the
  integration session (PR #1 / merge to `main`), and it matched every local
  prediction.
- No live Databricks validation, deployment, model calls, or Genie query has
  ever been run against this project. That remains true through chapter 01.

## Next task

Chapter 01's local work (platform map, scenarios, contract fixes, capability
checks) is complete. Integration was not authorized this session. When
authorized:

1. Push `series/01-know-your-platform` and open a PR into `main`. This chapter
   changes no bundle path either, so expect the same pattern as chapter 00:
   `Unit tests` runs, `Validate bundle`/`Deploy bundle` skip.
2. Before merging, re-confirm `deleteBranchOnMerge` is still `false`
   (`gh repo view ... --json deleteBranchOnMerge`) — it was disabled before
   chapter 00's merge, but re-check rather than assume it stayed that way.
3. Merge with a merge commit (not squash/rebase), same as chapter 00, so the
   ancestry-based local-branch-cleanup check in
   [branch workflow](branch-workflow.md) keeps working.
4. After merging and verifying, clean up the local branch using that same
   checklist. Never `-D`, never delete the remote.

Then start `series/02-quality-gate` from the then-current `main`. Its scope
(`docs/sentinel/roadmap.md`, "02 — Defend before damage spreads") is exactly
what chapter 01's Scenario A/B/C above were written to set up: batch identity,
persistent quarantine with reasons, quality metrics, and a publication gate
decision (reject individual records vs. withhold the Gold refresh) for
malformed values, duplicate leads, and missing campaign references.

Read [branch workflow](branch-workflow.md) before starting: create the new
chapter branch from current `main`, not from a locally cached ref.
