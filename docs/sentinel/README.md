# The Art of Data Defense

Bedoux Sentinel is the next part of `bedoux-databricks`: a small project about
protecting a fictional marketing lakehouse and investigating incidents with agents.
The existing medallion pipelines are the starting point. The defensive capabilities
below are planned, not claims about the current deployment.

The story follows one campaign batch through validation, evidence handling,
investigation, and recovery. Each chapter adds something a reader can reproduce.
The final video brings those pieces together.

## Start here

- [Roadmap](roadmap.md): chapter scope, completion criteria, and current status.
- [Branch workflow](branch-workflow.md): retained remote branches, local cleanup, and post tags.
- [Local development](../development.md): isolated uv environment and dependency updates.
- [Agent setup](agent-setup.md): Codex, Claude Code, and optional Jev development.
- [Writing guide](writing.md): voice, evidence, and the final video outline.
- [Live verification](live-verification.md): credential setup, what deploys
  automatically, and the chapter 02 demonstration plan.
- [Known gaps](known-gaps.md): durable cross-chapter register of deferred,
  not-fixed gaps — testing boundaries, evidence durability, unexercised
  code paths.
- [Session handoff](handoff.md): where the next session should begin.
- [Introduction draft](chapters/00-introduction.md): an unpublished launch post.

## Inspiration

[IBM Technology's video](https://www.youtube.com/watch?v=kjoQPn--F7A) connects eight
themes from Sun Tzu's *The Art of War* to cybersecurity. This project adapts those
themes to data contracts, publication gates, evidence, and agent permissions.
The controls are modern engineering choices, not historical prescriptions.

The book is traditionally attributed to Sun Tzu. "Roughly 2,500 years old" is an
introductory framing; its authorship and dating are debated. See the
[Library of Congress description](https://www.loc.gov/resource/gdcwdl.wdl_11410_001/?sp=10).

[Ray Amjad's Jev video](https://www.youtube.com/watch?v=ScvXFi4MUSc) inspired the
experiment with inexpensive classification and selective escalation. We will
measure whether that extra step helps on our incidents.

| Strategic theme | Where it appears |
| --- | --- |
| Know yourself and the threat | Part 01: assets, trust boundaries, incident scenarios |
| Prevent damage early | Part 02: validation and publication gates |
| Use deception | Part 03: synthetic canary marker; optional AWS decoy later |
| Respond and adapt | Part 04: investigation and controlled recovery |
| Prioritize critical assets | Parts 01 and 03: business impact and sensitive evidence |
| Maintain visibility and separation | Parts 01 and 06: dependency map, audit trail, permissions |
| Establish responsibility | Part 06: ownership, approvals, incident review |
| Use resources carefully | Part 05: measured Jev routing and escalation |

## Scope

Start with Databricks Free Edition, synthetic fixtures, and a local investigation
service. Keep AWS as an extension until required storage, identity, and access
features are verified. Track 1 remains the existing TPC-H demonstration.

Data defects and security incidents are different. A rejected row demonstrates
validation; it does not establish that an attack happened. A synthetic marker
blocked in a model payload proves that specific boundary check, not protection
against every way data might leave the platform.

The [current Free Edition limits](https://docs.databricks.com/aws/en/getting-started/free-edition-limitations)
must be checked before designing around external storage or enterprise security.
All implementation and publication states are tracked in the roadmap.
