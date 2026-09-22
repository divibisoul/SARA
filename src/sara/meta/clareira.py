"""SARA ↔ Clareira integration.

Composes the existing SARA ERU, provenance and VagusNerveBus authorities.
It does not create a second ERU or claim that an Android node changed state
unless an external runtime reports that change.
"""
from __future__ import annotations

import copy
import hashlib
import json
import threading
from dataclasses import dataclass, field
from typing import Any

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus
from sara.core.provenance import Provenance
from sara.infra.vagus_bus import VagusNerveBus
from sara.meta.eru_engine import ERU_Engine


CLAREIRA_SCHEMA_VERSION = "1.1.0"
CLAREIRA_BLUEPRINT_VERSION = "1.1.0"

BLUEPRINT_ROLES: tuple[str, ...] = (
    "NucleoRaizAlma",
    "NucleoDecisao",
    "NucleoPercepcao",
    "NucleoEstado",
    "NucleoExecutor",
    "NucleoVigilancia",
    "NucleoUsuario",
    "NucleoConfiguracao",
    "NucleoApps",
    "NucleoRede",
    "NucleoArmazenamento",
    "NucleoContexto",
    "NucleoSemantica",
    "NucleoSensores",
    "NucleoMemoria",
    "NucleoLinguagem",
    "NucleoEmocional",
    "NucleoRaciocinio",
    "NucleoControleMotor",
    "NucleoKernel",
)


@dataclass(frozen=True)
class ClareiraStateRecord:
    node_id: str
    level: str
    active: bool
    load_ratio: float
    temperature: float
    processing_rate: float
    timestamp: int


@dataclass
class ClareiraSubsystem:
    """Authoritative SARA adapter for Clareira evidence and vagal events."""

    eru: ERU_Engine
    provenance: Any
    bus: VagusNerveBus = field(default_factory=VagusNerveBus)

    NAME = "ClareiraSubsystem"
    VERSION = CLAREIRA_SCHEMA_VERSION
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = ("ERU_Engine", "ProvenanceTracker")
    CYCLE_PHASES = (
        CyclePhase.AUDIT,
        CyclePhase.VALIDATION,
        CyclePhase.PERSISTENCE,
        CyclePhase.MONITORING,
    )

    def __post_init__(self) -> None:
        self._latest_snapshot: dict[str, Any] | None = None
        self._latest_hash = ""
        self._snapshots: list[dict[str, Any]] = []
        self._vagal_commands: list[dict[str, Any]] = []
        self._lock = threading.RLock()

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [phase.value for phase in self.CYCLE_PHASES],
            "blueprint_version": CLAREIRA_BLUEPRINT_VERSION,
            "schema_version": CLAREIRA_SCHEMA_VERSION,
            "blueprint_class_count": len(BLUEPRINT_ROLES),
            "latest_snapshot_hash": self._latest_hash or None,
            "snapshot_count": len(self._snapshots),
            "vagal_command_count": len(self._vagal_commands),
            "bus": self.bus.describe(),
        }

    @staticmethod
    def _number(value: Any, *, default: float = 0.0) -> float:
        try:
            number = float(value)
        except (TypeError, ValueError):
            return default
        return number

    @classmethod
    def _validate_snapshot(cls, snapshot: dict[str, Any]) -> None:
        if not isinstance(snapshot, dict):
            raise ValueError("CLAREIRA_SNAPSHOT_MUST_BE_OBJECT")
        required = ("schemaVersion", "blueprintVersion", "metrics", "nodes", "channels", "homeostasis", "vagus")
        missing = [key for key in required if key not in snapshot]
        if missing:
            raise ValueError("CLAREIRA_SNAPSHOT_MISSING:" + ",".join(missing))
        if str(snapshot["schemaVersion"]) != CLAREIRA_SCHEMA_VERSION:
            raise ValueError("CLAREIRA_SCHEMA_VERSION_UNSUPPORTED")
        if not isinstance(snapshot["metrics"], dict):
            raise ValueError("CLAREIRA_METRICS_INVALID")
        if not isinstance(snapshot["nodes"], list):
            raise ValueError("CLAREIRA_NODES_INVALID")
        if not isinstance(snapshot["channels"], list):
            raise ValueError("CLAREIRA_CHANNELS_INVALID")
        if not isinstance(snapshot["homeostasis"], dict):
            raise ValueError("CLAREIRA_HOMEOSTASIS_INVALID")
        if not isinstance(snapshot["vagus"], dict):
            raise ValueError("CLAREIRA_VAGUS_INVALID")
        device = snapshot.get("deviceState")
        if device is not None:
            if not isinstance(device, dict):
                raise ValueError("CLAREIRA_DEVICE_STATE_INVALID")
            battery = device.get("batteryPercent")
            if not isinstance(battery, (int, float)) or not 0 <= float(battery) <= 100:
                raise ValueError("CLAREIRA_DEVICE_BATTERY_INVALID")
            if not isinstance(device.get("charging"), bool):
                raise ValueError("CLAREIRA_DEVICE_CHARGING_INVALID")
            if not isinstance(device.get("screenOn"), bool):
                raise ValueError("CLAREIRA_DEVICE_SCREEN_INVALID")
            if not isinstance(device.get("network"), str):
                raise ValueError("CLAREIRA_DEVICE_NETWORK_INVALID")
            if not isinstance(device.get("shizukuStatus"), str):
                raise ValueError("CLAREIRA_DEVICE_SHIZUKU_INVALID")

        for node in snapshot["nodes"]:
            if not isinstance(node, dict) or not isinstance(node.get("id"), str):
                raise ValueError("CLAREIRA_NODE_INVALID")
            if not isinstance(node.get("level"), str):
                raise ValueError("CLAREIRA_NODE_LEVEL_INVALID")
            active = node.get("active")
            if not isinstance(active, bool):
                raise ValueError("CLAREIRA_NODE_ACTIVE_INVALID")

    @classmethod
    def _normalize_node(cls, raw: dict[str, Any]) -> ClareiraStateRecord:
        load_ratio = cls._number(
            raw.get("loadRatio"),
            default=cls._number(raw.get("energy"), default=0.0)
            / max(1.0, cls._number(raw.get("energyCapacity"), default=100.0)),
        )
        return ClareiraStateRecord(
            node_id=str(raw["id"]),
            level=str(raw.get("level", "Unknown")),
            active=bool(raw.get("active", False)),
            load_ratio=max(0.0, min(1.0, load_ratio)),
            temperature=cls._number(raw.get("temperature")),
            processing_rate=cls._number(raw.get("processingRate"), default=1.0),
            timestamp=int(cls._number(raw.get("timestamp"), default=0.0)),
        )

    def _derive_homeostasis(self, nodes: list[ClareiraStateRecord]) -> dict[str, Any]:
        active = [node for node in nodes if node.active]
        if not active:
            return {
                "globalStress": 100.0 if nodes else 0.0,
                "energyScore": 0.0,
                "activeNodes": 0,
                "totalNodes": len(nodes),
            }
        total_stress = 0.0
        total_energy = 0.0
        for node in active:
            total_energy += node.load_ratio
            load_stress = max(0.0, node.load_ratio - 0.8) * 10.0
            thermal_stress = max(0.0, node.temperature - 0.7) * 4.0
            total_stress += load_stress + thermal_stress
        inactive_stress = max(0, len(nodes) - len(active)) * 2.0
        stress = min(100.0, total_stress + inactive_stress)
        return {
            "globalStress": round(stress, 6),
            "energyScore": round((total_energy / len(active)) * 100.0, 6),
            "activeNodes": len(active),
            "totalNodes": len(nodes),
        }

    def ingest_snapshot(
        self,
        snapshot: dict[str, Any],
        *,
        correlation_id: str,
        source: str = "SOUL_N01",
    ) -> dict[str, Any]:
        if not correlation_id.strip():
            raise ValueError("CLAREIRA_CORRELATION_ID_REQUIRED")
        self._validate_snapshot(snapshot)

        copied = copy.deepcopy(snapshot)
        nodes = [self._normalize_node(node) for node in copied["nodes"]]
        derived = self._derive_homeostasis(nodes)
        metrics = copied["metrics"]

        payload = {
            "schemaVersion": CLAREIRA_SCHEMA_VERSION,
            "blueprintVersion": str(copied.get("blueprintVersion")),
            "correlationId": correlation_id,
            "source": source,
            "timestamp": int(copied.get("timestamp") or 0),
            "observed": {
                "nodeCount": len(nodes),
                "channelCount": len(copied["channels"]),
                "activeVagusBranches": int(self._number(metrics.get("activeVagusBranches"))),
                "vagalTone": self._number(metrics.get("vagalTone")),
            },
            "nodes": [node.__dict__ for node in nodes],
            "reported_homeostasis": copy.deepcopy(copied["homeostasis"]),
            "derived_homeostasis": derived,
            "vagus": copy.deepcopy(copied["vagus"]),
            "device_state": copy.deepcopy(copied.get("deviceState")),
        }
        digest = hashlib.sha256(
            json.dumps(payload, sort_keys=True, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        ).hexdigest()
        snapshot_name = f"clareira:{correlation_id}:state"
        eru_hash = self.eru.freeze(snapshot_name, payload)

        record = {
            "schema_version": CLAREIRA_SCHEMA_VERSION,
            "blueprint_version": CLAREIRA_BLUEPRINT_VERSION,
            "correlation_id": correlation_id,
            "source": source,
            "hash": digest,
            "eru_hash": eru_hash,
            "observed_node_count": len(nodes),
            "observed_channel_count": len(copied["channels"]),
            "homeostasis": derived,
            "received_at": payload["timestamp"],
            "device_state": copy.deepcopy(payload["device_state"]),
        }
        with self._lock:
            self._latest_snapshot = record
            self._latest_hash = digest
            self._snapshots.append(copy.deepcopy(record))
            if len(self._snapshots) > 128:
                del self._snapshots[:-128]

        if self.provenance is not None:
            self.provenance.register(
                f"Clareira.snapshot.{correlation_id}",
                Provenance.HISTORICAL,
                "Estado recebido de runtime Clareira/SOUL e congelado pelo ERU",
                source=source,
            )
        return copy.deepcopy(record)

    async def issue_vagal_command(
        self,
        node_id: str,
        command: str,
        *,
        payload: dict[str, Any] | None = None,
        priority: float = 0.5,
        correlation_id: str,
        target: str = "SOUL_N01",
    ) -> dict[str, Any]:
        allowed = {"calm", "turbo", "reduce_thermal", "shutdown", "resume"}
        if command not in allowed:
            raise ValueError("CLAREIRA_VAGAL_COMMAND_UNSUPPORTED")
        if not node_id.strip() or not correlation_id.strip():
            raise ValueError("CLAREIRA_VAGAL_ID_REQUIRED")
        if target != "SOUL_N01":
            raise ValueError("CLAREIRA_VAGAL_TARGET_UNAUTHORIZED")

        event = await self.bus.publish(
            source="SARA",
            target=target,
            event_type="CLAREIRA_VAGAL_COMMAND",
            payload={
                "schema_version": CLAREIRA_SCHEMA_VERSION,
                "node_id": node_id,
                "command": command,
                "payload": copy.deepcopy(payload or {}),
                "priority": max(0.0, min(1.0, float(priority))),
                "correlation_id": correlation_id,
            },
        )
        record = copy.deepcopy(event)
        record["delivery_status"] = "PENDING"
        with self._lock:
            self._vagal_commands.append(record)
            if len(self._vagal_commands) > 256:
                del self._vagal_commands[:-256]

        if self.provenance is not None:
            self.provenance.register(
                f"Clareira.vagal.dispatch.{event['event_id']}",
                Provenance.INFERRED,
                "Comando vagal emitido pela autoridade SARA para SOUL N01; execução ainda não comprovada",
                source="ClareiraSubsystem.issue_vagal_command",
            )
        return {
            "accepted": True,
            "executed": False,
            "execution_status": "DISPATCHED_TO_EVENT_BUS",
            "event_id": event["event_id"],
            "correlation_id": correlation_id,
            "node_id": node_id,
            "command": command,
        }

    def pending_vagal_commands(self, *, limit: int = 32) -> list[dict[str, Any]]:
        if limit < 1:
            raise ValueError("CLAREIRA_VAGAL_LIMIT_INVALID")
        with self._lock:
            pending = [
                copy.deepcopy(item)
                for item in self._vagal_commands
                if item.get("delivery_status") == "PENDING"
            ]
        return pending[-min(limit, 128):]

    def acknowledge_vagal_command(
        self,
        event_id: str,
        *,
        executed: bool,
        execution_status: str,
    ) -> dict[str, Any]:
        if not event_id.strip():
            raise ValueError("CLAREIRA_VAGAL_EVENT_ID_REQUIRED")

        with self._lock:
            target = next(
                (item for item in reversed(self._vagal_commands)
                 if item.get("event_id") == event_id),
                None,
            )
            if target is None:
                raise ValueError("CLAREIRA_VAGAL_EVENT_NOT_FOUND")
            if target.get("delivery_status") != "PENDING":
                raise ValueError("CLAREIRA_VAGAL_EVENT_ALREADY_ACKNOWLEDGED")

            target["delivery_status"] = "EXECUTED" if executed else "DELIVERY_FAILED"
            target["execution_status"] = execution_status
            result = copy.deepcopy(target)

        if self.provenance is not None:
            self.provenance.register(
                f"Clareira.vagal.ack.{event_id}",
                Provenance.HISTORICAL,
                f"ACK recebido do SOUL N01: executed={executed}; status={execution_status}",
                source="ClareiraSubsystem.acknowledge_vagal_command",
            )
        return result

    def latest_snapshot(self) -> dict[str, Any] | None:
        return copy.deepcopy(self._latest_snapshot)

    def health_snapshot(self) -> dict[str, Any]:
        snapshot = self._latest_snapshot or {}
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "ready": True,
            "latest_snapshot_hash": self._latest_hash or None,
            "latest_snapshot": snapshot,
            "vagal_command_count": len(self._vagal_commands),
            "event_history": self.bus.get_history(limit=20),
        }

    def emit_trace(self, ctx: Any) -> None:
        if hasattr(ctx, "record"):
            ctx.record(
                "monitoring",
                self.NAME,
                True,
                snapshot_hash=self._latest_hash or None,
                snapshots=len(self._snapshots),
                vagal_commands=len(self._vagal_commands),
            )
