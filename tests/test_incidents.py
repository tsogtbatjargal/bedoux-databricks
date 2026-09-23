import json
import subprocess
import sys
from pathlib import Path

import pytest

from src.bedoux import model_call
from src.bedoux.evidence import CANARY_MARKER, FICTIONAL_SENSITIVE_LEAD
from src.bedoux.incidents import IncidentLog, investigate
from src.bedoux.model_call import BLOCKED, PENDING, REPORTED, ProviderTimeout
from tests.test_model_call import HEALTHY, VALID_REPORT, FakeProvider

REPO_ROOT = Path(__file__).resolve().parent.parent
SECRETS = ("000-00-0000", "4111-1111-1111-1111", "sk_fake_0000000000000000",
           "123-45-6789", CANARY_MARKER)


class Opaque:
    """str() carries the canary; the dict-level gate can't see it."""

    def __str__(self):
        return f"ref {CANARY_MARKER}"


INPUTS = {
    "healthy": HEALTHY,
    "healthy_with_redacted_ssn": {"source": "leads", "ssn": "123-45-6789",
                                  "stage": "qualified"},
    "canary_fixture": dict(FICTIONAL_SENSITIVE_LEAD),
    "nested_canary": {"rows": [{"lead_id": 1, "notes": f"ref {CANARY_MARKER}"}]},
    "copied_secret": {"ssn": "123-45-6789", "notes": "read out 123-45-6789"},
    "opaque_canary": {"source": "leads", "detail": Opaque()},
}


@pytest.fixture
def log(tmp_path):
    return IncidentLog(tmp_path / "incidents.jsonl")


# ---------------------------------------------------------------------------
# The incident is saved before the call, and survives the process dying
# ---------------------------------------------------------------------------


def test_incident_is_on_disk_and_pending_before_the_provider_is_called(log):
    seen_at_call_time = []

    class CheckingProvider(FakeProvider):
        def complete(self, payload, *, timeout_s):
            # A fresh reader, not the writer's state: this is what a
            # restarted process would see at this moment.
            seen_at_call_time.extend(IncidentLog(log.path).load().values())
            return super().complete(payload, timeout_s=timeout_s)

    provider = CheckingProvider()
    incident_id, _ = investigate(HEALTHY, provider, log)
    assert len(seen_at_call_time) == 1
    at_call = seen_at_call_time[0]
    assert at_call.incident_id == incident_id
    assert at_call.status == PENDING
    assert at_call.evidence_payload == provider.calls[0]["payload"]


def test_process_death_during_the_call_leaves_a_pending_incident(tmp_path):
    path = tmp_path / "incidents.jsonl"
    script = f"""
import os
from src.bedoux.incidents import IncidentLog, investigate

class DyingProvider:
    def complete(self, payload, *, timeout_s):
        os._exit(3)  # no cleanup, no outcome written

investigate({HEALTHY!r}, DyingProvider(), IncidentLog({str(path)!r}))
"""
    result = subprocess.run([sys.executable, "-c", script], cwd=REPO_ROOT,
                            capture_output=True, text=True, timeout=60)
    assert result.returncode == 3, result.stderr

    restarted = IncidentLog(path)
    pending = restarted.pending()
    assert len(pending) == 1
    assert pending[0].reason_codes == ()
    assert pending[0].evidence_payload == model_call.prepare_payload(HEALTHY)[0].text


def test_restart_keeps_earlier_incidents(log):
    first_id, _ = investigate(HEALTHY, FakeProvider(), log)
    second_id, _ = investigate(HEALTHY, FakeProvider(behavior=ProviderTimeout()),
                               IncidentLog(log.path))
    loaded = IncidentLog(log.path).load()
    assert set(loaded) == {first_id, second_id}
    assert loaded[first_id].status == REPORTED
    assert loaded[second_id].status == PENDING


def test_failed_save_means_no_provider_call(log):
    class BrokenLog(IncidentLog):
        def open_incident(self, evidence_payload):
            raise OSError("disk full")

    provider = FakeProvider()
    with pytest.raises(OSError):
        investigate(HEALTHY, provider, BrokenLog(log.path))
    assert provider.calls == []


def test_failed_outcome_write_leaves_the_incident_pending(log):
    class NoOutcomeLog(IncidentLog):
        def record_outcome(self, incident_id, outcome):
            raise OSError("disk full")

    with pytest.raises(OSError):
        investigate(HEALTHY, FakeProvider(), NoOutcomeLog(log.path))
    assert len(IncidentLog(log.path).pending()) == 1


def test_torn_last_line_is_skipped(log):
    incident_id, _ = investigate(HEALTHY, FakeProvider(), log)
    with open(log.path, "a", encoding="utf-8") as fh:
        fh.write('{"event": "opened", "incident_id": "half-writ')
    loaded = IncidentLog(log.path).load()
    assert list(loaded) == [incident_id]


# ---------------------------------------------------------------------------
# Outcomes are recorded against the same incident
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("behavior, status, codes", [
    (VALID_REPORT, REPORTED, ()),
    (ProviderTimeout(), PENDING, ("provider_timeout",)),
    (RuntimeError("boom"), PENDING, ("provider_error",)),
    ("not json", PENDING, ("malformed_response",)),
])
def test_outcome_is_recorded_against_the_incident(log, behavior, status, codes):
    incident_id, outcome = investigate(HEALTHY, FakeProvider(behavior=behavior), log)
    stored = IncidentLog(log.path).load()[incident_id]
    assert (outcome.status, outcome.reason_codes) == (status, codes)
    assert (stored.status, stored.reason_codes) == (status, codes)


def test_blocked_incident_is_recorded_with_no_evidence(log):
    incident_id, outcome = investigate(dict(FICTIONAL_SENSITIVE_LEAD), FakeProvider(), log)
    stored = IncidentLog(log.path).load()[incident_id]
    assert outcome.status == BLOCKED
    assert stored.status == BLOCKED
    assert stored.reason_codes == outcome.reason_codes
    assert stored.evidence_payload is None


# ---------------------------------------------------------------------------
# Saving an incident doesn't change the gate's decision
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("name", sorted(INPUTS))
def test_investigate_decides_exactly_like_call_model(log, name):
    direct_provider, logged_provider = FakeProvider(), FakeProvider()
    direct = model_call.call_model(INPUTS[name], direct_provider)
    _, logged = investigate(INPUTS[name], logged_provider, log)
    assert (logged.status, logged.reason_codes) == (direct.status, direct.reason_codes)
    assert len(logged_provider.calls) == len(direct_provider.calls)
    if logged.status == BLOCKED:
        assert logged_provider.calls == []


# ---------------------------------------------------------------------------
# The log never holds raw sensitive values or the canary
# ---------------------------------------------------------------------------


def test_log_file_never_contains_secrets_or_the_canary(log):
    for fields in INPUTS.values():
        investigate(fields, FakeProvider(), log)
    # Provider output that carries the canary: an error message and a valid
    # report. Only status and codes are stored, so neither reaches the file.
    investigate(HEALTHY, FakeProvider(behavior=RuntimeError(CANARY_MARKER)), log)
    report_with_canary = json.dumps({"summary": CANARY_MARKER, "uncertainty": "u",
                                     "proposed_recovery": "r"})
    investigate(HEALTHY, FakeProvider(behavior=report_with_canary), log)

    raw = Path(log.path).read_text(encoding="utf-8")
    assert raw.count("\n") == 2 * (len(INPUTS) + 2), "an opened and an outcome line each"
    for secret in SECRETS:
        assert secret not in raw


def test_stored_evidence_is_redacted_not_raw(log):
    incident_id, _ = investigate(INPUTS["healthy_with_redacted_ssn"], FakeProvider(), log)
    stored = json.loads(IncidentLog(log.path).load()[incident_id].evidence_payload)
    assert stored["ssn"] == "[REDACTED]"
    assert stored["stage"] == "qualified"

