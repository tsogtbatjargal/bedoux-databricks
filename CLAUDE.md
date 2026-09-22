# Claude Code project context

@AGENTS.md

Read `docs/sentinel/handoff.md` at the start of a new session.
Project skills are in `.claude/skills/`; their adapters point to the shared
instructions in `.agents/skills/`. Read the referenced skill before using it.

When compacting, preserve the authorized increment, branch/base, changed files,
decisions, failing/passing checks, unverified boundaries, and exact next task.
Keep historical narratives in linked chapter docs. Update the handoff before
clearing a session; load its archive only when a task needs historical evidence.
