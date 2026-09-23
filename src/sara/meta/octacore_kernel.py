"""SARA G0 kernel adapter for the Octacore system processor.

The kernel exposes existing SARA authorities as a bounded execution surface.
It does not reimplement ARA/ETR/ITR or create a second regeneration engine.
"""
from __future__ import annotations

from dataclasses import dataclass
from queue import Full, Queue
from threading import Event, Lock, Thread
from time import monotonic
import uuid
from typing import Any

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus


@dataclass
class _CycleRequest:
    input_text: str
    cycle_id: str | None
    correlation_id: str | None
    context: dict[str, Any] | None
    done: Event
    result: Any = None
    error: BaseException | None = None


class OctaCoreG0Kernel:
    NAME = "OctaCoreG0Kernel"
    VERSION = "1.1"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = (
        "RegenerativeLoop",
        "SistemaVivo",
        "ARA_Extended",
        "ETR_Extended",
        "DecisionTrace",
    )
    CYCLE_PHASES = tuple(CyclePhase)
    KERNEL_ID = "G0"
    NUCLEUS = "SARA"
    CAPABILITIES = (
        "sara.cycle",
        "sara.audit",
        "sara.regenerate",
        "sara.state",
        "sara.trace",
    )

    def __init__(self, *, queue_capacity: int = 32, vagus_bus: Any | None = None) -> None:
        self._queue_capacity = max(1, queue_capacity)
        self._vagus_bus = vagus_bus
        self._queue: Queue[_CycleRequest | None] = Queue(maxsize=self._queue_capacity)
        self._state_lock = Lock()
        self._inflight = 0
        self._throttle = 0
        self._halted = False
        self._last_latency_ms = 0
        self._vagus_bus: Any | None = None
        self._serial_lock = Lock()
        self._worker = Thread(target=self._worker_loop, name="sara-g0-octacore", daemon=True)
        self._worker.start()

    def bind_vagus(self, vagus_bus: Any) -> "OctaCoreG0Kernel":
        if vagus_bus is None:
            raise ValueError("VagusBus is required")
        self._vagus_bus = vagus_bus
        return self

    def _publish_health(
        self,
        correlation_id: str | None = None,
        latency_ms: int | None = None,
        request: _CycleRequest | None = None,
    ) -> None:
        bus = self._vagus_bus
        if bus is None:
            return
        if request is not None:
            correlation_id = correlation_id or request.correlation_id
        with self._state_lock:
            throttle = self._throttle
            halted = self._halted
            inflight = self._inflight
        event_payload = {
            "kernel": self.describe(),
            "queue_depth": self._queue.qsize(),
            "queue_capacity": max(1, self._queue_capacity // (2 ** throttle)),
            "inflight": inflight,
            "throttle_level": throttle,
            "halted": halted,
            "latency_ms": self._last_latency_ms if latency_ms is None else latency_ms,
            "job_correlation_id": getattr(request, "correlation_id", None),
        }
        try:
            bus.publish_sync(
                "SARA.G0",
                "VagusBus",
                "health.report",
                event_payload,
                status="EXECUTE",
                correlation_id=correlation_id,
                priority=100,
                ttl=5_000,
            )
        except Exception:
            # Telemetry must never alter G0 execution authority.
            return

    def _worker_loop(self) -> None:
        while True:
            request = self._queue.get()
            if request is None:
                self._queue.task_done()
                return
            started = monotonic()
            with self._state_lock:
                self._inflight += 1
            try:
                system = getattr(self, "_system_vivo", None)
                if system is None:
                    raise RuntimeError("G0_SYSTEM_NOT_BOUND")
                request.result = system.process(
                    request.input_text,
                    cycle_id=request.cycle_id,
                    context=request.context,
                )
                self._publish_health(request.correlation_id, request=request)
            except BaseException as exc:
                request.error = exc
                self._publish_health(request.correlation_id, request=request)
            finally:
                elapsed = int((monotonic() - started) * 1000)
                with self._state_lock:
                    self._inflight = max(0, self._inflight - 1)
                    self._last_latency_ms = elapsed
                self._publish_health(
                    request.correlation_id,
                    latency_ms=elapsed,
                    request=request,
                )
                request.done.set()
                self._queue.task_done()

    def bind(self, sistema_vivo: Any) -> "OctaCoreG0Kernel":
        if sistema_vivo is None:
            raise ValueError("SistemaVivo is required")
        with self._state_lock:
            self._system_vivo = sistema_vivo
        return self
