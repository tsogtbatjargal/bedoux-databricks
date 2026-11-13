# ADR 0008: Rules decide, models explain

Status: accepted (Track 4), 2026-11-13

## Context
A model-written incident report can be fluent and wrong. Its confidence is
not evidence. The plan for this track asks for root-cause diagnosis, but a
diagnosis that silently picks the remediation would hand the model authority.

## Decision
Incidents are opened only by deterministic checks. The investigator's report
must carry one label from a fixed list and citations that resolve in the
evidence it was sent (Sentinel's `send_payload` validation). A rules-based
classifier computes the reference label from the same store. Triage routes to a
runbook only on agreement; disagreement, a missing label, an invalid report or
instruction-like text in the evidence goes to a human. Runbooks are keyed by the
rules label.

## Consequences
- A wrong model label costs a human review, not a wrong remediation.
- The model's value is the cited explanation and the evidence trail, which is
  what the eval measures (required evidence, citations, forbidden tools).
- The classifier only covers known failure classes; a novel failure produces a
  disagreement or no label and therefore human triage, which is the intent.
