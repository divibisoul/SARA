"""Native SARA representation of the shared Clareira federation contract.
The HTTP/SOUL Mesh envelope remains authoritative for transport; this module only
validates and adapts the application-level ClareiraPacket.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any, Literal
import time, uuid

PacketType = Literal["Data","StateReport","DecisionRequest","DecisionResponse","Control","Heartbeat"]

@dataclass(frozen=True)
class ClareiraPacket:
    id: str
    data: str
    informational_value: float
    criticality: float
    packet_type: PacketType
    source_id: str
    destination_hint: str | None
    timestamp: int
    correlation_id: str
    metadata: dict[str, str | int | float | bool] = field(default_factory=dict)

def validate_clareira_packet(value: Any) -> bool:
    if not isinstance(value, dict):
        return False
    criticality = value.get("criticality")
    return (
        isinstance(value.get("id"), str) and bool(value["id"].strip())
        and isinstance(value.get("data"), str)
        and isinstance(value.get("informationalValue"), (int, float))
        and isinstance(criticality, (int, float)) and 0 <= float(criticality) <= 1
        and value.get("packetType") in {"Data","StateReport","DecisionRequest","DecisionResponse","Control","Heartbeat"}
        and isinstance(value.get("sourceId"), str) and bool(value["sourceId"].strip())
        and isinstance(value.get("timestamp"), (int, float))
        and isinstance(value.get("correlationId"), str) and bool(value["correlationId"].strip())
        and isinstance(value.get("metadata", {}), dict)
    )

def packet_to_dict(packet: ClareiraPacket) -> dict[str, Any]:
    return {
        "id": packet.id, "data": packet.data, "informationalValue": packet.informational_value,
        "criticality": packet.criticality, "packetType": packet.packet_type,
        "sourceId": packet.source_id, "destinationHint": packet.destination_hint,
        "timestamp": packet.timestamp, "correlationId": packet.correlation_id,
        "metadata": packet.metadata,
    }

def make_clareira_packet(
    data: str, source_id: str, correlation_id: str, *,
    criticality: float = 0.5, informational_value: float = 10.0,
    packet_type: PacketType = "Data", destination_hint: str | None = None,
    metadata: dict[str, str | int | float | bool] | None = None,
) -> ClareiraPacket:
    criticality = max(0.0, min(1.0, float(criticality)))
    return ClareiraPacket(
        id=f"clareira_{uuid.uuid4()}",
        data=data, informational_value=float(informational_value), criticality=criticality,
        packet_type=packet_type, source_id=source_id, destination_hint=destination_hint,
        timestamp=int(time.time() * 1000), correlation_id=correlation_id,
        metadata=metadata or {},
    )
