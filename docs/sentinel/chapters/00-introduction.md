# Part 00 — Shared development setup

Status: integrated. This chapter established the development workflow before
adding Sentinel's runtime controls.

## Technical deliverables

- `AGENTS.md`: shared scope, evidence, verification and authorization rules.
- `CLAUDE.md`: an adapter that imports the same project instructions.
- `.agents/skills/sentinel-chapter/`: the shared implementation/review workflow.
- `.claude/skills/sentinel-chapter/`: Claude's adapter to that workflow.
- [Agent setup](../agent-setup.md): session and review instructions.
- [Branch workflow](../branch-workflow.md): retained remote chapter snapshots,
  disposable working branches, checks and deployment conditions.
- [Handoff](../handoff.md): current technical state and continuation instructions.

The later editorial separation moved launch copy and the storytelling skill to
the `bedoux-sentinel-content` workspace. Personal Codex reasoning preferences
remain local. See [repository scope](../repository-scope.md).

This setup guides coding assistants; it is not a runtime security boundary.
