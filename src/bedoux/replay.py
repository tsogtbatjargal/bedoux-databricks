"""Duplicate-free replay of an accepted batch (chapter 04, step 5).

"Replay does not duplicate accepted records," in the version that can be
tested offline: `AcceptedRecords` is an in-memory stand-in for an accepted
table, keyed on a stable record id, and `replay_batch` re-runs Silver's
lead rules (quality.reconcile + classify_lead) over a batch and merges the
accepted rows into it by key. Replaying the same batch any number of times
leaves each accepted record exactly once.

The key is the natural key, `lead_id` -- the same key Silver's dedup rule
uses and the one the seeded generator reproduces on every run. Not
`_row_id`: that's a position in one generated list ("not a globally unique
batch or run ID", contracts-bedoux.md), so a reordered replay would give
the same lead a new one. Not `_ingest_ts`: it changes every load.

A merge, not an append: a key already present is left alone if the row is
identical, and replaced if it changed (a replay after a fix supersedes the
earlier version, like a MERGE ... WHEN MATCHED UPDATE). A key is never
added twice. A lead quarantined in an earlier replay and accepted in a
later one is inserted then.

Pure Python, no Spark. This is not the DLT pipeline: Track 2's Silver
tables are recomputed in full each run (contracts-bedoux.md), so the real
pipeline doesn't accumulate across runs this way at all. Nothing here
proves anything about Spark, DLT, or Delta MERGE.
"""

from dataclasses import dataclass

from . import quality

RECORD_KEY = "lead_id"


@dataclass(frozen=True)
class ReplayResult:
    inserted: int
    updated: int
    unchanged: int
    quarantined: int


class AcceptedRecords:
    def __init__(self):
        self._by_key = {}

    def merge(self, row):
        """Returns "inserted", "updated", or "unchanged"."""
        key = row[RECORD_KEY]
        if key not in self._by_key:
            self._by_key[key] = dict(row)
            return "inserted"
        if self._by_key[key] == row:
            return "unchanged"
        self._by_key[key] = dict(row)
        return "updated"

    def rows(self):
        return list(self._by_key.values())


def replay_batch(rows, store, known_campaign_ids):
    accepted, quarantined = quality.reconcile(
        rows, RECORD_KEY, quality.classify_lead, known_campaign_ids)
    counts = {"inserted": 0, "updated": 0, "unchanged": 0}
    for row in accepted:
        counts[store.merge(row)] += 1
    return ReplayResult(quarantined=len(quarantined), **counts)
