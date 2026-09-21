# Developing with Codex, Claude Code, and optionally Jev

Use whichever assistant fits the task. One implements; a fresh session in the
other reviews the actual diff and acceptance criteria. A second provider is useful
but optional. Do not run two writers in one checkout.

## What is configured

- `AGENTS.md` is the shared project guide. `CLAUDE.md` imports it.
- `.agents/skills/` holds the chapter and story workflows Codex discovers.
- `.claude/skills/` contains small adapters that read those same skill bodies.
- `.codex/config.toml` sets medium reasoning effort for routine work. It leaves
  model selection, credentials, sandbox, approvals, and external tools to the user.
- `handoff.md` holds current state. It is the continuity mechanism across providers;
  private assistant memory is not required to understand the project.

No provider credentials, global configuration, paid API calls, hooks, automatic
model routing, or Jev installation are included. Project instructions guide an
assistant; they do not enforce the runtime security controls planned for Sentinel.

## Start a session

Launch from the repository root after accepting its project trust prompt where
applicable. Restart an already-running assistant to discover newly added skills.

```bash
codex
# Or, when Astra is supported by the installed client/account:
codex -m gpt-6-astra

# A separate Claude Code session:
claude
```

Use `$sentinel-chapter` in Codex or `/sentinel-chapter` in Claude Code. The writing
equivalents are `$sentinel-story` and `/sentinel-story`. If discovery fails, ask the
assistant to read the corresponding `.agents/skills/.../SKILL.md` directly.

Suggested continuation prompt:

> Read AGENTS.md and docs/sentinel/handoff.md. Check the checkout, then continue
> the next local task recorded there using sentinel-chapter. Keep the current
> chapter scope, run appropriate checks, and update the handoff. Do not push,
> deploy, call paid APIs, or publish as part of this local task.

Suggested review prompt:

> Read AGENTS.md and the current chapter's acceptance criteria. Review the current
> branch against main, including uncommitted and untracked changes. Do not edit.
> Report concrete defects with file/line and impact, unsupported claims, and
> missing verification. If nothing is wrong, say that and name untested boundaries.

For a committed review, replace "main" with the known base SHA and name the target
SHA. Record reviewer/model, scope, findings, and disposition. Do not label a
self-review as an independent review. Parallel work, if requested, uses separate
worktrees with agreed file ownership.

## Optional Jev development experiment

Start with one advisory job, such as classifying review findings or selecting a
relevant runbook. Compare the suggestions against human-reviewed labels. Jev must
not approve shell commands, merge PRs, grant data access, or suppress failed tests.

When the user chooses to enable it, inspect TypeSafe's current
[official skill](https://github.com/typesafe-ai/skills/blob/main/skills/typesafe-ai/SKILL.md)
and [documentation](https://docs.typesafe.ai/). Select a pinned integration, review
its instructions/dependencies and what it sends externally, then configure it at
project scope. Use environment variables or the provider's credential store;
never put a key into committed config. Confirm API access and a spend limit before
a live benchmark. Do not auto-install an unpinned package in a startup hook.

If unavailable, continue with ordinary review and labeled fixtures. Distinguish
Jev used during development from the runtime incident router planned for part 05.
Codex/Claude Code subscriptions do not establish API access or a runtime budget.

## Local verification and sources

Python tests require `requirements-dev.txt`; CI uses Python 3.11. An isolated
virtual environment is preferable to changing the system interpreter. A docs-only
change can be checked with `git diff --check`, local-link checks, and skill/config
validation. Live bundle checks and model calls must be reported separately.

Configuration sources checked on 2026-09-21:

- [Codex project configuration](https://learn.chatgpt.com/docs/config-file/config-basic)
- [Codex skill discovery](https://learn.chatgpt.com/docs/build-skills)
- [Claude Code imports](https://code.claude.com/docs/en/memory)
- [Claude Code skills](https://code.claude.com/docs/en/skills)

Installed client versions and checks from this preparation session are recorded
in the handoff. A new session should inspect its own environment before assuming
those versions, account access, or configuration loading still apply.
