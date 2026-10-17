# ADR 0002: Responsible-gaming flags are explainable rules, not a model (yet)

Status: accepted (Track 3), 2026-10-16

## Context
Responsible-gaming decisions affect real people and must be defensible to a
compliance reviewer and a regulator. A model needs labelled outcomes, which a new
program doesn't have, and its output is harder to explain.

## Decision
Start with four explainable rules (loss chasing, deposit spike, long session,
self-exclusion breach) with documented thresholds. Every flag carries a
plain-language explanation. `src/aglc/rules.py` is the tested spec. Gold mirrors it.

## Consequences
- Every flag traces to a threshold; reviewers can challenge the threshold, not a black box.
- `gold_gaming_player_daily` is a feature table: the same grain and columns a
  later model would train on. ML can be added as a second signal, not a replacement.
- Rules miss patterns they don't name, and thresholds here are illustrative,
  not clinical guidance.
