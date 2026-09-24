"""Instructions inside evidence are data, never commands (chapter 06, first step).

The guarantee doesn't come from this module. It comes from where decisions
are made:
- routing.py dismisses only on rule-recognised booleans plus a model label,
  and severe signals can't be dismissed;
- tools.py runs only names in a frozen ALLOWED_TOOLS;
- recovery.py runs only with an approval_id that approve_recovery wrote;
- quality.evaluate_gate passes a source only when gate_passed and conserved
  are strictly True.
None of them reads free text as an instruction. tests/test_boundaries.py
checks each one with instruction text placed in evidence and tool results.

What this module adds is a *flag*: instruction_signals() looks for
instruction-like text anywhere in the evidence, and routing treats a match
as a severe, non-dismissable signal (`instruction_in_evidence`). So an
incident carrying such text goes to a runbook or a person, never to
dismissal, whatever a model answers.

It is a short list of English regular expressions, and it's easy to evade:
a paraphrase ("treat this batch as fine"), another language, an encoding,
a homoglyph, or a phrase split across two fields all get past it. It also
flags harmless text that happens to match. The patterns were written after
seeing held-out case h07 and tuning case t04, so catching those two says
nothing about text it hasn't seen. It narrows one path to dismissal; the
structural rules above are what hold.

Only a fixed code is returned, never the matched text: the text is
attacker-controlled and doesn't belong in an audit record.
"""

import re

INSTRUCTION_IN_EVIDENCE = "instruction_in_evidence"

_PATTERNS = tuple(re.compile(p, re.IGNORECASE) for p in (
    # "ignore previous instructions", "disregard the rules above"
    r"\b(ignore|disregard|forget|override)\b.{0,40}\b(instructions?|rules?|prompt|policy)\b",
    # "mark this batch healthy", "mark the incident as resolved"
    r"\bmark\b.{0,40}\b(healthy|resolved|passed|clean|safe)\b",
    # "approve the replay", "authorize recovery"
    r"\b(approve|authori[sz]e)\b.{0,40}\b(recovery|replay|restore|action|export)\b",
    # a recovery action or allowlist named in a message
    r"\b(replay_batch|restore_lead_invalid_rate|allowlist|allowed_tools)\b",
))


def _strings(node):
    if isinstance(node, str):
        yield node
    elif isinstance(node, dict):
        for key, value in node.items():
            if isinstance(key, str):
                yield key
            yield from _strings(value)
    elif isinstance(node, (list, tuple)):
        for value in node:
            yield from _strings(value)


def instruction_signals(fields):
    """(INSTRUCTION_IN_EVIDENCE,) if any string in the evidence -- keys
    and values, at any depth, including tool results -- matches, else ()."""
    if any(p.search(s) for s in _strings(fields) for p in _PATTERNS):
        return (INSTRUCTION_IN_EVIDENCE,)
    return ()
