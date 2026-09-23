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

    def __init__(self, *, queue_capacity: int = 32) -> None:
        self._queue_capacity = max(1, queue_capacity)
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

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "slot": self.KERNEL_ID,
            "nucleus": self.NUCLEUS,
            "type": "system_gpu_regenerative_kernel",
            "silicon_gpu": False,
            "authoritative": True,
            "capabilities": list(self.CAPABILITIES),
            "delegation": "existing SARA HTTP/runtime contracts",
            "queue_capacity": self._queue_capacity,
        }

    def bind_vagus(self, vagus_bus: Any) -> "OctaCoreG0Kernel":
        if vagus_bus is None:
            raise ValueError("VagusNerveBus is required")
        self._vagus_bus = vagus_bus
        vagus_bus.subscribe("signal.throttle", self._on_vagus_signal)
        vagus_bus.subscribe("signal.halt", self._on_vagus_signal)
        vagus_bus.subscribe("signal.resume", self._on_vagus_signal)
        vagus_bus.subscribe("signal.degrade", self._on_vagus_signal)
        return self

    def _on_vagus_signal(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("event_type", "")).strip()
        payload = event.get("payload")
        payload = payload if isinstance(payload, dict) else {}
        if event_type in ("signal.throttle", "signal.degrade"):
            try:
                level = int(payload.get("level", 1 if event_type == "signal.degrade" else -1))
            except (TypeError, ValueError) as exc:
                raise ValueError("G0 throttle signal requires integer level") from exc
            if level < 0:
                raise ValueError("G0 throttle signal requires level")
            self.set_throttle(level)
        elif event_type == "signal.halt":
            self.halt()
        elif event_type == "signal.resume":
            self.resume()

    def health(self) -> dict[str, Any]:
        with self._state_lock:
            throttle = self._throttle
            halted = self._halted
            inflight = self._inflight
            latency = self._last_latency_ms
        effective_capacity = max(1, self._queue_capacity // (2**throttle))
        report = {
            "slot": self.KERNEL_ID,
            "nucleus": self.NUCLEUS,
            "status": "HALTED" if halted else "READY",
            "queue_depth": self._queue.qsize(),
            "queue_capacity": effective_capacity,
            "base_queue_capacity": self._queue_capacity,
            "inflight": inflight,
            "throttle_level": throttle,
            "last_latency_ms": latency,
            "vagus_control_plane": self._vagus_bus is not None,
        }
        return report

    def set_throttle(self, level: int) -> None:
        if level < 0 or level > 3:
            raise ValueError("G0 throttle level must be 0..3")
        with self._state_lock:
            self._throttle = level

    def halt(self) -> None:
        with self._state_lock:
            self._halted = True

    def resume(self) -> None:
        with self._state_lock:
            self._halted = False

    def cycle(
        self,
        sistema_vivo: Any,
        input_text: str,
        *,
        cycle_id: str | None = None,
        correlation_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Any:
        with self._state_lock:
            if self._halted:
                raise RuntimeError("G0_HALTED")
            throttle = self._throttle
        effective_capacity = max(1, self._queue_capacity // (2**throttle))
        if self._queue.qsize() >= effective_capacity:
            raise RuntimeError("G0_BACKPRESSURE")

        request = _CycleRequest(
            input_text=str(input_text),
            cycle_id=cycle_id,
            correlation_id=correlation_id or cycle_id or f"g0-{uuid.uuid4()}",
            context=dict(context) if isinstance(context, dict) else context,
            done=Event(),
        )
        try:
            self._queue.put_nowait(request)
        except Full as exc:
            raise RuntimeError("G0_BACKPRESSURE") from exc

        if not request.done.wait(timeout=120.0):
            raise TimeoutError("G0_CYCLE_TIMEOUT")
        if request.error is not None:
            raise request.error
        return request.result

    def audit(self, ara_extended: Any, etr_extended: Any, input_text: str) -> dict[str, Any]:
        with self._serial_lock:
            semantic = ara_extended.detect_semantic(input_text)
            structural = ara_extended.detect_structural(input_text)
            relational = ara_extended.detect_relational(input_text)
            flaws = [*ara_extended.detect(input_text), *semantic, *structural, *relational]
            ethical = etr_extended.validate_multi_framework(input_text)
            provenance = ara_extended.meta_audit_complete()
            return {
                "operation": "audit",
                "flaws": [getattr(item, "__dict__", str(item)) for item in flaws],
                "count": len(flaws),
                "semantic": [getattr(item, "__dict__", str(item)) for item in semantic],
                "structural": [getattr(item, "__dict__", str(item)) for item in structural],
                "relational": [getattr(item, "__dict__", str(item)) for item in relational],
                "ethical": getattr(ethical, "__dict__", str(ethical)),
                "provenance": provenance,
            }

    def regenerate(self, ara_extended: Any, etr_extended: Any, input_text: str) -> dict[str, Any]:
        with self._serial_lock:
            semantic = ara_extended.detect_semantic(input_text)
            structural = ara_extended.detect_structural(input_text)
            relational = ara_extended.detect_relational(input_text)
            flaws = [*ara_extended.detect(input_text), *semantic, *structural, *relational]
            regenerated = ara_extended.regenerate_semantic(input_text, flaws)
            ethical = etr_extended.validate_multi_framework(regenerated.transformed)
            return {
                "operation": "regenerate",
                "original": regenerated.original,
                "transformed": regenerated.transformed,
                "applied_rules": list(regenerated.applied_rules),
                "plan_steps": list(regenerated.plan_steps),
                "integrity_hash": regenerated.integrity_hash,
                "preserved_length": regenerated.preserved_length,
                "ethical": getattr(ethical, "__dict__", str(ethical)),
            }

    def state(self, sistema_vivo: Any) -> dict[str, Any]:
        return sistema_vivo.state()

    def trace(self, trace: Any, cycle_id: str) -> dict[str, Any]:
        entries = trace.query({"cycle_id": cycle_id})
        return {
            "cycle_id": cycle_id,
            "integrity": trace.verify(),
            "entries": [getattr(entry, "__dict__", str(entry)) for entry in entries],
        }

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
            except BaseException as exc:
                request.error = exc
            finally:
                request.done.set()
                elapsed = int((monotonic() - started) * 1000)
                with self._state_lock:
                    self._inflight = max(0, self._inflight - 1)
                    self._last_latency_ms = elapsed
                self._publish_health(elapsed, request)
                self._queue.task_done()

    def _publish_health(self, latency_ms: int, request: _CycleRequest) -> None:
        if self._vagus_bus is None:
            return
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
            "latency_ms": latency_ms,
            "job_correlation_id": request.correlation_id,
        }
        try:
            self._vagus_bus.publish_sync(
                "G0",
                "VAGUS",
                "health.report",
                event_payload,
                status="EXECUTE",
                correlation_id=request.cycle_id,
                priority=100,
                ttl=5000,
            )
        except Exception:
            # Telemetry must never break a completed SARA cycle.
            return

    def bind(self, sistema_vivo: Any) -> "OctaCoreG0Kernel":
        if sistema_vivo is None:
            raise ValueError("SistemaVivo is required")
        with self._state_lock:
            self._system_vivo = sistema_vivo
        return self
