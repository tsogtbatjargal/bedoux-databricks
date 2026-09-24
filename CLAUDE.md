# Claude Code project context

@AGENTS.md

Read `docs/sentinel/handoff.md` at the start of a new session.
Project skills are in `.claude/skills/`; their adapters point to the shared
instructions in `.agents/skills/`. Read the referenced skill before using it.

When compacting, preserve the authorized increment, branch/base, changed files,
decisions, failing/passing checks, unverified boundaries, and exact next task.
Keep technical history in linked chapter docs. Editorial drafts belong to the
separate content workspace; see `docs/sentinel/repository-scope.md`. Update the
handoff before clearing a session; consult Git history when needed.
