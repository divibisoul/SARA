from sara.meta.eru_engine import ERU_Engine


class RecordingTemporal:
    def __init__(self):
        self.events = []

    def insert(self, event):
        self.events.append(event)


def test_snapshot_limit_is_a_soft_threshold_and_keeps_prior_states_queryable():
    temporal = RecordingTemporal()
    engine = ERU_Engine(temporal=temporal, max_snapshots=1)
    original = {"phase": "before", "payload": {"sequence_index": 1}}
    followup = {"phase": "after", "payload": {"sequence_index": 2}}

    original_hash = engine.freeze("historical-baseline", original)
    followup_hash = engine.freeze("integrated-state", followup)

    assert original_hash != followup_hash
    assert engine.has_snapshot("historical-baseline")
    assert engine.has_snapshot("integrated-state")
    assert engine.snapshot_state("historical-baseline") == original
    assert engine.snapshot_state("integrated-state") == followup

    description = engine.describe()
    assert description["snapshots"] == 2
    assert description["snapshot_limit"] == 1
    assert description["snapshot_limit_reached"] is True
    assert description["snapshot_retention"] == "append_only"

    pressure_events = [
        event for event in temporal.events
        if event.get("event") == "eru_snapshot_limit_reached"
    ]
    assert len(pressure_events) == 1
    assert pressure_events[0]["name"] == "historical-baseline"
    assert pressure_events[0]["state_hash"] == original_hash
    assert pressure_events[0]["limit"] == 1
    assert pressure_events[0]["snapshot_count"] == 1
    assert pressure_events[0]["reason"] == "soft_limit_preserves_history"

    assert engine.compare("historical-baseline", "integrated-state").lost != ["__missing_snapshot__"]
