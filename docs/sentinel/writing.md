# Writing the series

Write as a developer explaining something specific to a colleague. Use the
author's actual observations and choices. Natural writing comes from concrete
details and honest limits, not invented anecdotes or deliberate mistakes.

## A useful post shape

Aim for roughly 150–250 words when that suits the chapter. Start with the problem,
connect it briefly to a strategic idea, describe the engineering choice, show the
result, and name a limitation. End with the next technical question if it follows
naturally. This is a guide, not a sentence template to repeat eight times.

- Prefer "The batch failed this check" to "I built a revolutionary defense layer."
- Explain one decision in enough detail that another engineer could question it.
- Use first person only for work/decisions attributable to the author. Do not
  invent an outage, customer, discovery, emotion, or career anecdote.
- Avoid stock openings, grand claims, engagement bait, excessive emojis, and
  repeated "not X, but Y" phrasing. Hashtags are optional.
- Mention AI assistance when relevant to the development story. The author owns
  the decisions and review; do not imply every line was manually written.
- Distinguish data reliability from security. A synthetic attack fixture does not
  prove production security. Name the environment in which a result was observed.
- Use historical themes as interpretations. Verify quotations and translations
  before quoting; otherwise paraphrase and credit the source.

## Evidence before publication

Every results post needs a reproducible input/seed, the code commit, the command
or job run, observed output, and known limitations. A measured number needs its
measurement source. A target or estimate must be labeled. Remove credentials,
personal workspace identifiers, and sensitive payloads from screenshots and traces.

Keep a draft, evidence notes, and final public URL with the chapter. Add those
files when they have content; do not create empty folders for all future posts.
Link the exact demonstrated post tag or SHA. Mark unpushed references as pending.
No assistant publishes on the user's behalf without a publication request.

## Final video

Target 4–6 minutes: inspiration and business question; healthy dashboard and bad
batch; quarantine and publication gate; redacted evidence and investigation;
approved replay and reconciliation; measured evaluation and a limitation.

Show the terminal or dashboard performing the actual steps. Label recorded/cached
model responses, simulation, and edited waiting periods. Make the repository
instructions sufficient to reproduce the scenario after the video ends.
