"""SARA — Monitoramento: StormMonitor.
Status: IMPLEMENTED
"""
from __future__ import annotations
import os
import threading
import time
from dataclasses import dataclass, field
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.clock import now_iso


@dataclass
class MonitorReport:
    monitoring_id: str
    capability: str
    samples: int
    duration_s: float
    anomalies: list[dict] = field(default_factory=list)


class StormMonitor:
    NAME = "StormMonitor"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MONITORING
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.MONITORING,)

    def __init__(self, interval_s: float = 0.5) -> None:
        self._interval = interval_s
        self._sessions: dict[str, dict] = {}

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "active_sessions": len(self._sessions),
        }

    def start(self, capability: str, duration_h: float) -> str:
        mid = f"storm-{capability}-{int(time.time()*1000)}"
        stop_flag = threading.Event()
        session = {
            "id": mid, "capability": capability, "stop": stop_flag,
            "samples": [], "start_ts": now_iso(),
            "start_time": time.time(), "duration_h": duration_h,
        }
        self._sessions[mid] = session

        def worker() -> None:
            deadline = session["start_time"] + duration_h * 3600
            while not stop_flag.is_set() and time.time() < deadline:
                try:
                    load = os.getloadavg()[0]
                except (OSError, AttributeError):
                    load = 0.0
                session["samples"].append({"ts": now_iso(), "load_avg": load})
                time.sleep(self._interval)

        t = threading.Thread(target=worker, name=mid, daemon=True)
        t.start()
        return mid

    def stop(self, monitoring_id: str) -> MonitorReport:
        s = self._sessions.get(monitoring_id)
        if s is None:
            raise KeyError(f"monitoring_id '{monitoring_id}' não existe")
        s["stop"].set()
        duration = time.time() - s["start_time"]
        anomalies = self._detect_anomalies(s["samples"])
        return MonitorReport(s["id"], s["capability"], len(s["samples"]),
                             duration, anomalies)

    def collect_metrics(self, monitoring_id: str) -> list[dict]:
        return list(self._sessions[monitoring_id]["samples"])

    def anomalies(self, monitoring_id: str) -> list[dict]:
        return self._detect_anomalies(self._sessions[monitoring_id]["samples"])

    @staticmethod
    def _detect_anomalies(samples: list[dict]) -> list[dict]:
        if not samples:
            return []
        loads = [s["load_avg"] for s in samples]
        mean = sum(loads) / len(loads)
        variance = sum((x - mean) ** 2 for x in loads) / len(loads)
        std = variance ** 0.5
        anomalies = []
        for s in samples:
            if std > 0 and abs(s["load_avg"] - mean) > 3 * std:
                anomalies.append({"ts": s["ts"], "value": s["load_avg"]})
        return anomalies

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("monitoring", self.NAME, True,
                       active_sessions=len(self._sessions))