# ADR 0009: Agents propose, humans apply

Status: accepted (Track 4), 2026-11-13

## Context
The investigator could plausibly fix things itself: replay quarantine, bump a
contract, rerun a job. Each of those writes to shared state. The project's
existing rule (AGENTS.md) is that model output never widens permissions.

## Decision
Agent tools are read-only and allowlisted in code; prohibited verbs are refused
before the allowlist is checked. Remediation is a runbook proposal plus the
validations that must pass. `runbooks.request_approval` records an
`approval_requested` event with status `awaiting_approval`; no code path in
`src/adp` applies it. Azure deployment is a manual workflow with a protected
GitHub environment and OIDC, never a push trigger.

## Consequences
- Zero agent-triggered writes is a property of the code, checked by tests and
  by the eval's `forbidden_tool_executions` metric.
- Recovery is slower than an autonomous fix. That is the accepted cost.
