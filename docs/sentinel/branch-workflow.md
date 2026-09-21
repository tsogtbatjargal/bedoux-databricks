# Branches that readers can revisit

`main` holds the integrated project. Each chapter has a retained `series/NN-name`
branch. Create it when that chapter starts, from `main` containing the previous
chapter. The branch is cumulative: a reader gets a runnable project at that stage.

Recommended post tags are `post/00-introduction`, `post/01-know-your-platform`,
and so on, matching the branch suffix. A tag identifies the exact demonstrated
commit even if a branch later needs a correction. Published tags never move.

## Chapter lifecycle

1. Check for uncommitted work and inspect local/remote branch state. Preserve
   unfinished work. Synchronize `main` without rewriting history when appropriate.
2. Create the chapter branch from integrated `main`. Implement and verify its
   acceptance criteria. Save the draft and sanitized evidence with the chapter.
3. Review the diff, refresh the handoff, and commit the finished chapter when
   authorized. For an independent review, name the base commit and target commit;
   include untracked files if reviewing work before it is committed.
4. Push/open a PR when requested. Prefer a merge commit to keep chapter ancestry
   straightforward. Retain the head branch after merging; do not pass a delete
   option to PR tooling. `main` must include the chapter before the next starts.
5. After verifying the final demonstration commit, create an annotated post tag
   on that exact commit and push the explicit branch/tag refs when authorized.
   Do not tag unfinished work just to fill the index.
6. Verify the public links, then publish only when the user requests publication.
   Record the commit, tag, PR, evidence, and actual LinkedIn URL in the index.

There is no requirement to publish immediately after merging. Keep implementation
and publication status separate. Verify GitHub's automatic head-branch deletion
setting before the first merge and disable it when repository settings changes
are authorized. Never assume a retained local branch means a remote one exists.

## Deployment coupling

Originally `.github/workflows/ci.yml` deployed the bundle on every push to `main`,
including documentation-only merges, and on every `workflow_dispatch` even with
its job-run checkbox off. Chapter 00 separated documentation from deployment:

- Pull requests are unfiltered. Every proposed change still runs tests and
  `databricks bundle validate`, documentation included.
- Pushes to `main` skip the workflow when *every* changed file is documentation
  or agent configuration (`**.md`, `docs/**`, `.agents/**`, `.claude/**`,
  `.codex/**`, `.gitignore`, `LICENSE`). A merge touching pipeline code,
  `databricks.yml`, `resources/**`, `tests/**`, or the workflow itself still runs
  the full test → validate → deploy chain. A commit mixing documentation with
  pipeline code deploys, because `paths-ignore` skips only when nothing else
  changed.
- `workflow_dispatch` now takes an explicit `deploy` checkbox, default off.
  Dispatching without it runs the checks and touches no workspace. `run_job`
  still requires the deploy job, so it cannot run a job without a deployment.

So merging a documentation-only chapter into `main` no longer deploys, but
merging a chapter that changes the pipeline does. Treat that second case as a
deployment decision and confirm it before pushing.

These conditions were verified by evaluating the filter patterns and the deploy
job's `if` expression against real commits in this repository; they have not been
observed in a live GitHub Actions run. Note that a documentation-only push to
`main` produces no CI run at all, so it reports no checks — intended here, but it
means a required status check on `push` would never be satisfied by such a merge.

## Corrections and references

Treat a published chapter branch as a snapshot. Make later fixes on a new branch
from `main`; use a new correction tag and explain the change. Do not merge later
chapters back into old chapter branches. Do not rebase published branches.

For this repository the reference patterns are:

- Branch: `https://github.com/tsogtbatjargal/bedoux-databricks/tree/series/02-quality-gate`
- Snapshot: `https://github.com/tsogtbatjargal/bedoux-databricks/tree/post/02-quality-gate`
- Exact code: a GitHub permalink using the full commit SHA.

These are patterns, not currently published links. Only use a link in a public
post after the corresponding ref exists remotely and has been checked.

## Publication register

No chapter has been published by this workflow yet. Add one row per publication:

| Part | Branch | Demonstrated commit | Post tag | PR | Evidence path | LinkedIn URL |
| --- | --- | --- | --- | --- | --- | --- |

Only chapter 00 is being prepared locally. Future chapter branches and post tags
should be created at their lifecycle steps, not pre-created at a shared baseline.
