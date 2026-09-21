# Agent instructions

The shared project instructions now live in [AGENTS.md](../AGENTS.md).
Codex reads that file directly; [CLAUDE.md](../CLAUDE.md) imports it for Claude Code.

Start a new session with the [handoff](sentinel/handoff.md). The
[agent setup](sentinel/agent-setup.md) explains the development and review workflow.

The old instructions here described manually configured workspace paths. For the
bundle managed by this repository, use `databricks.yml` and `resources/*.yml` as
the configuration source, and `src/` for pipeline code. This documentation update
does not migrate or bind any existing workspace resources.
