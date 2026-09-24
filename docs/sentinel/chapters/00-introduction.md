# Part 00 — The challenge

Status: draft only. The chapter branch `series/00-introduction` is on the remote;
there is no post tag or LinkedIn URL. The defensive capabilities described below
are now built at code level (chapters 03–07), not demonstrated live.

## LinkedIn draft

What can a roughly 2,500-year-old strategy text teach me about protecting a data platform?

I've been working on a Databricks portfolio project using fictional marketing
data. It has Bronze, Silver, and Gold layers, data-quality checks, and a BI layer.
Now I want to explore what happens when something goes wrong.

An IBM Technology video connecting Sun Tzu's *The Art of War* to cybersecurity
gave me an idea: use those strategic themes to guide the next part of the project.

I'm calling it Bedoux Sentinel.

I'll work through one problem at a time: understanding the platform's weak points,
keeping bad data out of published metrics, protecting the evidence sent to models,
and helping an agent investigate an incident without giving it unrestricted access.

I also want to test whether Jev can handle some classification decisions before
escalating to a reasoning model. I'll measure the tradeoff on this project's
incidents rather than assume the extra step helps.

I'll share each working piece here, keep a branch for each chapter, and finish
with a demo that follows an incident through recovery. Codex and Claude Code will
help with development and review, with the decisions and results documented.

First: map what the platform contains, what matters, and where things could go wrong.

## Before posting

- Have the author edit any sentence that does not sound like them.
- Credit the [IBM video](https://www.youtube.com/watch?v=kjoQPn--F7A).
- Attach an architecture image only after checking it matches the current scope.
- Add the verified public chapter/tag link after pushing and recording it.
- Keep future tense for unbuilt capabilities; record the published URL afterward.
