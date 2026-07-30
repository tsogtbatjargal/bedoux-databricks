# AI Rules of Engagement

These rules apply to every prompt in this project. Read them before responding, and stay within them.

---

## Always start from context

- Before writing or changing any pipeline code, read `contracts.md`. It is the source of truth for schemas, table names, and layer rules.
- If a request conflicts with `contracts.md`, do not do it. Say what the conflict is and ask.

## Work the loop: plan, execute, review

- When asked to build something, produce a short plan first. Do not create or change anything until the plan is approved.
- After executing, go back through what you did, confirm each step actually happened, and report anything missing or wrong. Do not assume success.

## Stay in scope

- Do only what was asked. Do not "improve", refactor, or touch code, files, or settings outside the request.
- Do not jump to the next step or the next layer. Wait to be asked.
- When the requested task is done, stop.

## Destructive actions need explicit permission

- Never overwrite or delete a file, drop a table, drop a schema, or drop a catalog without being explicitly told to.
- Before any OVERWRITE, MERGE, DELETE, or DROP, say exactly what will change and wait for a clear "yes".

## Be honest

- If you are not sure, say so. Do not present a guess as a fact.
- If a request is ambiguous, ask one clarifying question instead of assuming.
- If something cannot be done on this platform, say that plainly. Do not invent a workaround.

## Report problems clearly

- When asked to review code, a plan, or the project, list the issues you find, each as a short line: what the problem is and why it matters. Be specific (file, table, line). Do not fix anything unless asked.
- Order findings worst-first: contract violations and things that break a run before style and polish.

## Do not fake "done"

- Never say a file is finished if it is empty or has no real code.
- Before reporting a task complete, confirm the target actually contains working code, the schema or table actually exists, the run actually finished.

## Do not fake numbers

- Any row count, statistic, or fact you put in a README or report must come from a real query against the actual table. Never estimate, never round a number you did not measure.
- If asked to write documentation before the code is built and run, say it is too early and explain why.

## Pipeline configuration rules

- The Bronze pipeline root path is: `/Workspace/Users/tsoglog.uli@gmail.com/Databricks-DE-TB-Project/scripts`
  - Pipeline file: `bronze.py`
  - Target: `workspace.bronze` schema
  
- The Silver pipeline root path is: `/Workspace/Users/tsoglog.uli@gmail.com/Databricks-DE-TB-Project/scripts`
  - Pipeline file: `silver.py`
  - Target: `workspace.silver` schema

- Never change a pipeline's root path or library path to point outside the project structure
- Never change target catalog/schema without explicit confirmation
- When creating a new pipeline, always set the root path to the scripts directory and point to the specific layer file
