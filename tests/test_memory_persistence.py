import json

import pytest

from sara.memory.regenerative_memory import RegenerativeMemory
from sara.memory.temporal_vector_db import TemporalVectorDB


def test_regenerative_memory_round_trip_is_atomic_and_integrity_checked(tmp_path):
    path = tmp_path / "memory.json"
    source = RegenerativeMemory(persist_path=str(path))
    source.store({"cycle": "c1", "state": "alpha"}, label="c1")
    assert source.persist_if_configured() is True
    assert path.exists()

    restored = RegenerativeMemory(persist_path=str(path))
    assert restored.load_if_configured() is True
    assert restored.latest().state == {"cycle": "c1", "state": "alpha"}
    assert restored.verify_integrity() is True


def test_regenerative_memory_rejects_tampered_state(tmp_path):
    path = tmp_path / "memory.json"
    source = RegenerativeMemory()
    source.store({"cycle": "c1", "state": "alpha"})
    source.persist(str(path))
    payload = json.loads(path.read_text(encoding="utf-8"))
    payload[0]["state"]["state"] = "tampered"
    path.write_text(json.dumps(payload), encoding="utf-8")

    with pytest.raises(ValueError, match="REGN_MEMORY_INTEGRITY_FAILED"):
        RegenerativeMemory().load(str(path))


def test_temporal_vector_db_round_trip_and_integrity(tmp_path):
    path = tmp_path / "temporal.json"
    source = TemporalVectorDB(persist_path=str(path))
    rid = source.insert({"cycle_id": "c1", "state": "alpha"}, vector=[1.0, 0.0])
    assert source.persist_if_configured() is True

    restored = TemporalVectorDB(persist_path=str(path))
    assert restored.load_if_configured() is True
    record = restored.by_id(rid)
    assert record is not None
    assert restored.verify_record(rid) is True
    assert record.vector == [1.0, 0.0]


def test_temporal_vector_db_rejects_missing_integrity(tmp_path):
    path = tmp_path / "temporal.json"
    path.write_text(json.dumps([{
        "id": "x", "data": {}, "ts": "2026-01-01T00:00:00Z",
        "inserted_at": "2026-01-01T00:00:00Z", "vector": None
    }]), encoding="utf-8")

    with pytest.raises(ValueError, match="TEMPORAL_VECTOR_INTEGRITY_MISSING"):
        TemporalVectorDB().load(str(path))
