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

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus, SaraModule


@dataclass
class _CycleRequest:
    input_text: str
    cycle_id: str | None
    correlation_id: str | None
    context: dict[str, Any] | None
    done: Event
    result: Any = None
    error: BaseException | None = None


class OctaCoreG0Kernel(SaraModule):
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
        self._vagus_bound = False
        self._serial_lock = Lock()
        self._worker = Thread(target=self._worker_loop, name="sara-g0-octacore", daemon=True)
        self._worker.start()
        if vagus_bus is not None:
            self.bind_vagus(vagus_bus)

    def set_vagus_bus(self, vagus_bus: Any) -> "OctaCoreG0Kernel":
        if vagus_bus is None:
            raise ValueError("VagusBus is required")
        self._vagus_bus = vagus_bus
        self._vagus_bound = False
        return self

    def bind_vagus(self, vagus_bus: Any) -> "OctaCoreG0Kernel":
        if vagus_bus is None:
            raise ValueError("VagusBus is required")
        if self._vagus_bus is not vagus_bus:
            self._vagus_bus = vagus_bus
            self._vagus_bound = False
        if not self._vagus_bound:
            vagus_bus.subscribe("signal.throttle", self._on_vagus_signal)
            vagus_bus.subscribe("signal.halt", self._on_vagus_signal)
            vagus_bus.subscribe("signal.resume", self._on_vagus_signal)
            vagus_bus.subscribe("signal.degrade", self._on_vagus_signal)
            self._vagus_bound = True
        return self

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

    def health(self) -> dict[str, Any]:
        with self._state_lock:
            throttle = self._throttle
            halted = self._halted
            inflight = self._inflight
            latency = self._last_latency_ms
        effective_capacity = max(1, self._queue_capacity // (2 ** throttle))
        return {
            "slot": self.KERNEL_ID,
            "nucleus": self.NUCLEUS,
            "status": "HALTED" if halted else "READY",
            "queue_depth": self._queue.qsize(),
            "queue_capacity": effective_capacity,
            "base_queue_capacity": self._queue_capacity,
            "inflight": inflight,
            "throttle_level": throttle,
            "last_latency_ms": latency,
        }

    def set_throttle(self, level: int) -> None:
        if level < 0 or level > 3:
            raise ValueError("G0 throttle level must be 0..3")
        with self._state_lock:
            self._throttle = level
        self._publish_health()

    def halt(self) -> None:
        with self._state_lock:
            self._halted = True
        self._publish_health()

    def resume(self) -> None:
        with self._state_lock:
            self._halted = False
        self._publish_health()

    def _on_vagus_signal(self, event: dict[str, Any]) -> None:
        event_type = str(event.get("event_type", "")).strip()
        payload = event.get("payload")
        if not isinstance(payload, dict):
            payload = {}
        signal = event_type.split(".", 1)[1] if "." in event_type else event_type
        if signal in {"throttle", "degrade"}:
            raw_level = payload.get("level", 1 if signal == "degrade" else 0)
            try:
                self.set_throttle(int(raw_level))
            except (TypeError, ValueError):
                return
        elif signal == "halt":
            self.halt()
        elif signal == "resume":
            self.resume()

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
        effective_capacity = max(1, self._queue_capacity // (2 ** throttle))
        if self._queue.qsize() >= effective_capacity:
            raise RuntimeError("G0_BACKPRESSURE")
        self.bind(sistema_vivo)
        cid = cycle_id or correlation_id or str(uuid.uuid4())
        request = _CycleRequest(
            input_text=str(input_text),
            cycle_id=cid,
            correlation_id=correlation_id or cid,
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
            base = list(ara_extended.detect(input_text))
            semantic = list(getattr(ara_extended, "detect_semantic", lambda _t: [])(input_text))
            structural = list(getattr(ara_extended, "detect_structural", lambda _t: [])(input_text))
            relational = list(getattr(ara_extended, "detect_relational", lambda _t: [])(input_text))
            flaws = [*base, *semantic, *structural, *relational]
            ethical = etr_extended.validate_multi_framework(input_text)
            return {
                "operation": "audit",
                "flaws": [getattr(item, "__dict__", str(item)) for item in flaws],
                "count": len(flaws),
                "semantic": [getattr(item, "__dict__", str(item)) for item in semantic],
                "structural": [getattr(item, "__dict__", str(item)) for item in structural],
                "relational": [getattr(item, "__dict__", str(item)) for item in relational],
                "ethical": getattr(ethical, "__dict__", str(ethical)),
                "provenance": getattr(ara_extended, "meta_audit_complete", lambda: {})(),
            }

    def regenerate(self, ara_extended: Any, etr_extended: Any, input_text: str) -> dict[str, Any]:
        with self._serial_lock:
            flaws = [
                *ara_extended.detect(input_text),
                *getattr(ara_extended, "detect_semantic", lambda _t: [])(input_text),
                *getattr(ara_extended, "detect_structural", lambda _t: [])(input_text),
                *getattr(ara_extended, "detect_relational", lambda _t: [])(input_text),
            ]
            regenerated = ara_extended.regenerate_semantic(input_text, flaws)
            ethical = etr_extended.validate_multi_framework(regenerated.transformed)
        return {
            "operation": "regenerate",
            "original": regenerated.original,
            "transformed": regenerated.transformed,
            "applied_rules": list(regenerated.applied_rules),
            "plan_steps": list(regenerated.plan_steps),
            "integrity_hash": regenerated.integrity_hash,
            "preserved_length": getattr(regenerated, "preserved_length", len(regenerated.original)),
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
                with self._serial_lock:
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
