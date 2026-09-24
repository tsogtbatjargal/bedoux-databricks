# Technical repository and editorial workspace

`bedoux-databricks` holds runnable code, tests, synthetic fixtures, dependency
locks, bundle/CI configuration, contracts, technical architecture, runbooks,
recorded evidence, chapter implementation notes and the technical handoff.
The local `scripts/full_demo.py` is a reproducible technical example and stays here.

`bedoux-sentinel-content` is the separate workspace for LinkedIn copy, video
narration, publication tracking, research notes, writing guidance and editorial
graphics. It owns `sentinel-story` and its Claude adapter. The author maintains
that workspace separately; this repo has no runtime or test dependency on it.
No public content-repository URL has been established. Do not invent one or add
machine-specific filesystem links to the technical documentation.

## Shared agent files

Keep these versioned because they describe the project's technical workflow:

- `AGENTS.md`: scope, evidence rules and verification.
- `CLAUDE.md`: a small adapter importing the shared instructions.
- `.agents/skills/sentinel-chapter/SKILL.md`: the shared technical skill.
- `.claude/skills/sentinel-chapter/SKILL.md`: its Claude adapter.

Personal model/reasoning choices, tokens, local permissions, environment files
and private session data stay local. `.codex/config.toml` is ignored; its existing
local contents were preserved when it was removed from tracking. Shared Codex
configuration could be added deliberately later if a technical requirement needs
it; a reasoning preference alone does not require a committed config file.

## Migration and history

The separation starts from commit `ede2901766fddbe40263ee601aa3d8eee37a8491`.
Seven chapter drafts and the chapter 07 video script were copied to the content
workspace before removal here. Their evidence links use that exact source SHA.
The writing guide, storytelling skill, inspiration notes and introduction SVG
also moved. The technical `docs/architecture.drawio` remains here.

Retained remote `series/00-*` through `series/07-*` branches stay historical
snapshots. Their old trees and Git history still contain editorial files; this
cleanup does not rewrite or force-push those references. New work from the cleaned
main keeps editorial assets separate. Make technical corrections on a new branch.

Before pushing this cleanup, back up or version the content workspace separately.
Pushing this repository cannot upload files outside its root. Original imported
material is also recoverable from the source SHA above.
