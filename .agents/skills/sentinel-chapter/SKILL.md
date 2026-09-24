---
name: sentinel-chapter
description: Implement, review, or hand off a Bedoux Sentinel chapter using its acceptance criteria, retained branch workflow, and recorded evidence. Use for work on the Art of Data Defense series.
---

# Work on a Sentinel chapter

Paths below are relative to the repository root.

Read `docs/sentinel/handoff.md`, the selected section of
`docs/sentinel/roadmap.md`, and `docs/sentinel/branch-workflow.md` before changing
chapter work. Check the actual branch and diff; do not assume the handoff is current.

For implementation, select the smallest next increment that satisfies the user's
request. Read the relevant layer contract before changing a pipeline. Keep a
chapter independently demonstrable with a synthetic scenario and a normal control.
When a contract disagrees with code, state the discrepancy and the intended
behavior before implementing the authorized change.

For review, inspect the real diff and relevant callers/tests. Focus on loss of
evidence, duplicate replay, publication gates, permission boundaries, model
failures, and claims the demonstration does not establish. Report file/line,
trigger, impact, and missing verification. Do not manufacture findings or edit
as a side effect of a review-only request.

Use existing checks appropriate to the change. Record environment, input/seed,
command, observed result, and unverified integration points in the chapter's
evidence. Model-generated reports are not substitutes for execution evidence.

Finish by updating the handoff: completed work, checks, open issues, uncommitted
state, and next task. Keep the roadmap's implementation status separate from
publication status. Editorial drafts and `sentinel-story` belong to the separate
`bedoux-sentinel-content` workspace; see `docs/sentinel/repository-scope.md`.
Publishing, merging, deployments, and paid API experiments need authorization
covering those actions; do not re-ask when the user has already provided it.
