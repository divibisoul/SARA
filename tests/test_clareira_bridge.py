from shared.clareira_contract import make_clareira_packet, packet_to_dict
from sara.federation.clareira_bridge import ClareiraBridge

def test_clareira_bridge_accepts_valid_packet():
    bridge = ClareiraBridge()
    packet = make_clareira_packet("entrada", "N07", "corr-1")
    result = bridge.ingest(packet_to_dict(packet))
    assert result["accepted"] is True
    assert result["correlationId"] == "corr-1"
    assert bridge.metrics()["packets"]["ingested"] == 1

def test_clareira_bridge_rejects_invalid_packet():
    bridge = ClareiraBridge()
    try:
        bridge.ingest({"id": "bad"})
    except ValueError as exc:
        assert str(exc) == "INVALID_CLAREIRA_PACKET"
    else:
        raise AssertionError("invalid packet was accepted")
