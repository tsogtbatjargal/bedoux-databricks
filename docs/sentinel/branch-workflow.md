# Branches that readers can revisit

`main` holds the integrated project. Each chapter starts from that version of
`main` on a `series/NN-name` branch. Retain the **remote** chapter branch for
readers. Once merged and safely preserved remotely, remove its local branch to
keep the checkout tidy. The user explicitly chose this policy.

Post tags such as `post/00-introduction` identify the exact demonstrated commit.
Published tags never move. Create future branches when their chapters start, not
all at once from today's baseline.

## Branch namespace: chapters vs. working branches

The `series/` prefix is shared by two different kinds of branch, and only one
of them is covered by "retain the remote branch" above:

- **Chapter branches** — exactly one per chapter, named `series/NN-name`
  matching the row in [roadmap.md](roadmap.md)'s table (`series/00-introduction`,
  `series/01-know-your-platform`, `series/02-quality-gate`,
  `series/03-protect-evidence`, and so on as later chapters start). These are
  **archival and retained unconditionally, remote, forever** — they're what the
  "Reference patterns" section below gives a citable URL for, and what a
  published post or a future reader might browse directly.
- **Working branches** — everything else in the `series/` namespace, plus
  every `feat/` and `docs/` branch: fix
  rounds (`series/02-quality-gate-fixes`, `series/03-evidence-leak-fix`),
  draft/housekeeping rounds (`series/02-post-draft`), and cross-cutting prep
  work (`series/00-claude-efficiency`, `series/docs-alignment`). These exist
  because a chapter branch is a published snapshot per "Corrections and
  references" below — later fixes get their own branch rather than reopening
  or rebasing an already-retained one. They are **ordinary and safe to delete
  after merging**, the same as any feature branch: every commit on them
  remains permanently reachable through its merge commit on `main` and through
  its (immutable) PR page on GitHub, so deleting the source branch loses no
  evidence and breaks no citation. This project's citations are commit SHAs
  and PR numbers (see every chapter doc's "Status" line and "Before posting"
  checklist), never a working-branch name or URL.

The one exception, stated so it's not a surprise later: if a fix branch's
commit ever becomes *the* demonstrated commit cited in the [publication
register](#publication-register) below — i.e. the branch itself, not just its
already-merged SHA, is what a live publication points a reader at — treat that
one branch as archival from that point on. Nothing currently published makes
this apply to any existing branch; the publication register is still empty.

## Chapter lifecycle

1. Inspect the checkout and preserve unfinished changes. Start the next chapter
   from `main` after the preceding chapter has been integrated.
2. Implement and verify the chapter. Save its evidence and post draft; update
   the handoff with observed results and remaining work.
3. Commit/push/open a PR within the user's authorization. Wait for `Unit tests`
   to pass on the PR's head commit before merging, docs-only PRs included.
   Prefer a merge commit so the chapter's commits remain ancestors of `main`.
4. Keep the remote PR head branch after merging. Check GitHub's automatic
   head-branch deletion setting before the first merge; disable it when settings
   changes are authorized. Do not use PR-tool options that delete the head branch.
5. Tag the final demonstrated commit when authorized. Push the explicit tag,
   verify public links, and record publication separately from implementation.
6. Clean up the merged local chapter branch using the checks below.

## Local branch cleanup

The user permits this after a merge; a new confirmation is not needed when the
checks pass. Before deleting a specific local chapter branch:

- Require a clean working tree and verify it is not checked out in any worktree.
- Fetch `origin` and verify the chapter branch still exists on the server with
  `git ls-remote --exit-code --heads origin refs/heads/series/NN-name`.
- Require its local tip to equal the fetched remote chapter tip. A stale tracking
  ref alone is not evidence of preservation.
- Require the chapter tip to be an ancestor of both local `main` and
  `origin/main`, using `git merge-base --is-ancestor`. Update local `main`
  with a fast-forward if needed.
- Switch to `main` (or another appropriate working branch), then delete only the
  verified local ref with `git branch -d series/NN-name`.

Use the exact branch name in place of the example. Never use `-D`, wildcard
deletion, or `git push --delete`. If a squash/rebase merge means the ancestry
check fails, leave the local branch and explain; do not force the cleanup.
Never delete `main`, a remote chapter branch, or a published tag.

Restore a local copy later with
`git switch --track origin/series/NN-name`. Remote retention is the archival
requirement; a local branch is a working convenience.

## CI and deployment

Local tests run on every pull request, push to `main`, and manual dispatch.
There are no workflow-level path exclusions. Use the always-running
`Unit tests` check for local test status; workspace jobs may be skipped.

A pinned `dorny/paths-filter` action detects changes to `src/**`,
`resources/**`, or `databricks.yml`. For PRs it uses the changed-file API; for
main pushes it compares the pre-push commit. Failed detection prevents dependent
workspace jobs. Tests use the same locked uv environment as local development.

- Pipeline/bundle PRs also validate the bundle, but never deploy.
- Pipeline/bundle pushes to `main` validate, then deploy after successful tests.
- Documentation, tests, dependency/tooling files, and workflow-only changes run
  local tests without deployment. Mixed changes deploy if they affect bundle paths.
- Manual dispatch validates the bundle; `deploy` must be selected to deploy.
  `run_job` only runs the pipeline after a successful opted-in deployment.
  Dispatch is not restricted to `main`: choosing another branch and checking
  `deploy` deploys *that* branch's bundle to the dev target. The old workflow
  behaved the same way. Treat the branch selector as part of the deployment
  decision, or add a ref condition if that capability is not wanted.

The preparation changes no bundle paths, so integrating it does not require a
one-off deployment under this workflow. This supersedes the earlier
`paths-ignore` approach in commit `b9250aa`. The workflow in the pushed revision
controls that push; there is no need to find a special route around the old file.

If a future bundle starts consuming other paths (for example runtime dependency
files or packaged artifacts), extend the filter in the same change. A missing
required credential can still prevent live validation. Local CI checks do not
prove the workflow has run successfully on GitHub.

Third-party actions are pinned by commit SHA with the intended version in a
trailing comment. `databricks/setup-cli` is now pinned to `d76f84c...c963b7`
(tag `v1.17.0`), confirmed against the GitHub API during the chapter 00
integration session. The `dorny/paths-filter` (`ceb8a2b...c5cc9d`, `v4`) and
`astral-sh/setup-uv` (`c771a70...ca235ff9`, `v9.0.0`) SHAs, written offline,
were resolved the same session: each SHA matches its intended tag's commit
exactly.

## Corrections and references

Treat a published remote branch as a snapshot. Make later fixes on a new branch
from `main`, with a new correction tag. Do not merge future chapters back into old
branches or rebase published history.

Reference patterns (use only after verifying the remote refs):

- Branch: `https://github.com/tsogtbatjargal/bedoux-databricks/tree/series/02-quality-gate`
- Snapshot: `https://github.com/tsogtbatjargal/bedoux-databricks/tree/post/02-quality-gate`
- Exact code: a GitHub permalink using the full commit SHA.

## Publication register

No chapter has been published by this workflow yet. Add a row per publication:

| Part | Branch | Demonstrated commit | Post tag | PR | Evidence path | LinkedIn URL |
| --- | --- | --- | --- | --- | --- | --- |
