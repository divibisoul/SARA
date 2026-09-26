"""Clareira ↔ SARA bridge.
Adapts the shared application packet into the existing SARA runtime without
duplicating ARA/ETR/ITR or changing their authority.
"""
from __future__ import annotations
from collections import deque
from time import time
from typing import Any
from shared.clareira_contract import ClareiraPacket, packet_to_dict, validate_clareira_packet

class ClareiraBridge:
    CONTRACT_VERSION = "1.0.0"

    def __init__(self) -> None:
        self.started_at_ms = int(time() * 1000)
        self.ingested = self.processed = self.dropped = self.errored = self.in_flight = 0
        self.latencies_ms: deque[float] = deque(maxlen=128)

    def ingest(self, raw: dict[str, Any]) -> dict[str, Any]:
        if not validate_clareira_packet(raw):
            self.errored += 1
            raise ValueError("INVALID_CLAREIRA_PACKET")
        packet = ClareiraPacket(
            id=str(raw["id"]), data=str(raw["data"]),
            informational_value=float(raw["informationalValue"]),
            criticality=float(raw["criticality"]), packet_type=raw["packetType"],
            source_id=str(raw["sourceId"]), destination_hint=raw.get("destinationHint"),
            timestamp=int(raw["timestamp"]), correlation_id=str(raw["correlationId"]),
            metadata=dict(raw.get("metadata", {})),
        )
        self.ingested += 1
        self.in_flight += 1
        return {
            "accepted": True,
            "contractVersion": self.CONTRACT_VERSION,
            "correlationId": packet.correlation_id,
            "packet": packet_to_dict(packet),
        }

    def complete(self, started_ms: int) -> None:
        self.processed += 1
        self.in_flight = max(0, self.in_flight - 1)
        self.latencies_ms.append(max(0.0, float(int(time() * 1000) - started_ms))

    def fail(self) -> None:
        self.errored += 1
        self.in_flight = max(0, self.in_flight - 1)

    def metrics(self) -> dict[str, Any]:
        values = sorted(self.latencies_ms)
        pick = lambda p: values[min(len(values)-1, int((len(values)-1)*p))] if values else 0.0
        return {
            "capturedAtMs": int(time() * 1000),
            "nodes": {"total": 1, "active": 1, "errored": self.errored},
            "channels": {"total": 1, "open": 1},
            "packets": {
                "ingested": self.ingested, "processed": self.processed,
                "dropped": self.dropped, "errored": self.errored, "inFlight": self.in_flight,
            },
            "latencyMs": {"last": values[-1] if values else 0.0, "p50": pick(.50), "p95": pick(.95), "max": values[-1] if values else 0.0},
            "uptimeMs": int(time() * 1000) - self.started_at_ms,
        }

clareira_bridge = ClareiraBridge()
