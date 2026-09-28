from datetime import datetime, timezone

from sara.rgo.bugshield_adapter import from_bugshield


def test_bugshield_detection_only_preserves_source_and_leaves_dual_unresolved():
    payload = {
        "schema_version": "1.2.0",
        "scan_id": "scan-1",
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "scanner": {"name": "BugShield", "version": "1.2.0"},
        "scope": {"input_hash": "sha256:input"},
        "finding": {
            "id": "f-1",
            "type": "BUG",
            "category": "static",
            "description": "finding",
            "epistemic_mode": "INSPECTION",
            "verification_state": "UNVERIFIED",
            "evidence": [{"id": "ev-1", "kind": "static", "ref": "lint://1"}],
        },
    }
    env = from_bugshield(payload)
    assert env.dual_status.value == "UNRESOLVED"
    assert env.extensions["bugshield"] == payload
    env.validate()
