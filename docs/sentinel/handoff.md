# Session handoff

This is the technical handoff. Check Git before continuing; recorded state is
context, not authorization to merge, deploy, publish or call paid APIs.

## Current implementation

Chapters 00–07 are integrated at code level. **372 local tests pass**
(`uv run --locked python -m pytest -q`, run on `docs/separate-editorial-content`
before commit). The editorial separation changes no Python, tests, dependencies,
resources or bundle configuration.

- **02:** live fault, restore and replay evidence is recorded in
  [chapter-02-evidence.md](chapter-02-evidence.md).
- **03:** redaction/canary checks are local. The append-only Delta evidence log
  is demonstrated live, including failed UPDATE/DELETE and duplicate rows on
  retry. See [chapter-03-evidence.md](chapter-03-evidence.md).
- **04–06:** investigation, bounded tools, approval/replay, routing and adversarial
  boundaries use scripted providers and local fixtures. No real model has been
  called; real executors, table readers and provider evaluation remain deferred.
- **07:** `scripts/full_demo.py` provides a reproducible local example using
  fakes, tied to historical Databricks evidence. It does not demonstrate a live
  agent, redaction in the complete path or the composed finale. See
  [chapter 07](chapters/07-full-demo.md) and [known gaps](known-gaps.md).

Detailed acceptance maps and technical history remain in
[the chapters](README.md#start-here) and [roadmap](roadmap.md).
Do not promote code-level completion into a live-evidence claim.

## Latest change: Track 3 started (branch `track3/01-contract-generator`)

Branched from `main` at `3675ff5`. Not merged and not pushed. Merging to `main`
deploys (CI), so integrating is a deployment decision.

Added: `docs/contracts-aglc.md`; `docs/adr/0001`–`0006`; `src/aglc/` (generator,
expectations, rules, legacy, reconcile, governance, DLT bronze/silver/gold, three
notebook tasks); `resources/aglc.yml` (3 pipelines + `aglc_lakehouse_job`); three
`aglc_*` variables in `databricks.yml`; `tests/test_aglc.py`.

Checks: `uv run --locked python -m pytest -q` → **418 passed** (372 existing + 46
Track 3). `py_compile` on all `src/aglc/*.py`, YAML parse and `git diff --check` clean.
**Not run:** `databricks bundle validate` (the CLI profile `bedoux-databricks` shows
`Valid: NO`, so re-login is needed), any deploy or job run.

Implemented, not demonstrated live: Spark Gold mirroring `rules.py`; DLT column
masks and row filter (Free Edition support unverified, `aglc_enforce_governance`
toggles them); reconcile gate; grants (off by default, `aglc_apply_grants`).

Next useful task: re-login, `databricks bundle validate`, deploy to dev, run
`aglc_lakehouse_job` once with `aglc_enforce_governance=true`. If masks or filters
are unsupported, rerun with `false` and record that in ADR 0004. Then: a parity
check of `gold_rg_player_flags` against `rules.player_flags`, a dev/prod target
split (per-target catalog or schema prefix, since one Free Edition workspace),
a Genie space over RG Gold, a diagram, and a 2-minute demo script.

## Latest change: editorial separation

Delivered from the working branch `docs/separate-editorial-content`, based on
`ede2901766fddbe40263ee601aa3d8eee37a8491`, through a documentation-only PR.

At the user's request, editorial material moved to the separate
`bedoux-sentinel-content` workspace: seven post drafts, the final video script,
writing guidance, inspiration notes, introduction SVG and storytelling skill.
Copies were verified before removal. That workspace's README and migration
record identify the destinations and original source commit.

This repo retains technical chapter records, runbooks, evidence, the architecture
source, reproducible demo, AGENTS.md, CLAUDE.md and the shared chapter skill with
its Claude adapter. The existing `.codex/config.toml` remains on disk but is
removed from tracking and ignored because it only holds a personal preference.
See [repository scope](repository-scope.md).

Chapter 00's title is "Shared development setup" in the roadmap, the series
README and the chapter doc; the former roadmap title, "The challenge", was
editorial framing.

Retained remote chapter snapshots are untouched; they still include their
historical editorial material. The external content folder is not a Git repo
and has no configured remote. Pushing this repo does not back it up.

## Verification

Migration copy checks passed for all eight extracted draft/script sections and
the moved writing guide, SVG, adapter and inspiration text. A final check of
relative links and heading anchors in all Markdown files found 135 links, none
broken. Both shared skills and both
Claude adapters passed the skill validator; their file references and CLAUDE
imports resolve. Fresh-session discovery was not exercised.

The local Codex config is unchanged, valid TOML, untracked and ignored. Diff
whitespace checks passed. Runtime, tests, demo, dependencies, bundle/CI, live
evidence and the technical diagram are unchanged; pytest passed (372) and live
validation was not run. No job or provider was called.

## Branches and next step

- Remote: `main` and the eight retained chapter branches, `series/00-introduction`
  through `series/07-full-demo`. The working branch `docs/separate-editorial-content`
  was deleted after merging.
- Local: `main` only.

Wait for `Unit tests` on a PR's head before merging, documentation-only included.

Preserve/version the external content workspace; it has no Git remote.
Existing drafts there still
need an editorial status review before publication. Technical architecture
updates and all live provider work remain separate tasks.
