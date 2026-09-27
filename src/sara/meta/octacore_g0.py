"""Octacore G0 kernel boundary for SARA.

G0 is a software execution boundary over the existing SARA regenerative
runtime. Regeneration remains owned by ARA/ETR/ITR inside SARA; this module
only provides admission, serialization, backpressure and telemetry.
"""
from __future__ import annotations

from dataclasses import dataclass
from queue import Full, Queue
from threading import Event, Lock, Thread
from time import monotonic
from typing import Any

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus


@dataclass
class _CycleRequest:
    system: Any
    input_text: str
    cycle_id: str | None
    context: dict[str, Any] | None
    done: Event
    result: Any = None
    error: BaseException | None = None
    queued_at: float = 0.0


class OctacoreG0Kernel:
    NAME = "OctacoreG0Kernel"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    CYCLE_PHASES = tuple(CyclePhase)
    DEPENDENCIES = (
        "SistemaVivo",
        "RegenerativeLoop",
        "ARA_Extended",
        "ETR_Extended",
        "DecisionTrace",
    )
    KERNEL_ID = "G0"
    NUCLEUS = "SARA"
    CAPABILITIES = (
        "sara.cycle",
        "sara.audit",
        "sara.regenerate",
        "sara.state",
        "sara.trace",
    )

    def __init__(self, queue_capacity: int = 32) -> None:
        self.queue_capacity = max(1, int(queue_capacity))
        self._queue: Queue[_CycleRequest | None] = Queue(maxsize=self.queue_capacity)
        self._lock = Lock()
        self._halted = False
        self._throttle = 0
        self._inflight = 0
        self._completed = 0
        self._failed = 0
        self._last_latency_ms = 0.0
        self._worker = Thread(target=self._run, name="sara-octacore-g0", daemon=True)
        self._worker.start()

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "slot": self.KERNEL_ID,
            "nucleus": self.NUCLEUS,
            "type": "system_gpu_regenerative_kernel",
            "authoritative": True,
            "silicon_gpu": False,
            "capabilities": list(self.CAPABILITIES),
            "queue_capacity": self.queue_capacity,
        }

    def health(self) -> dict[str, Any]:
        with self._lock:
            throttle = self._throttle
            halted = self._halted
            inflight = self._inflight
            completed = self._completed
            failed = self._failed
            latency = self._last_latency_ms
        effective_capacity = max(1, self.queue_capacity // (2 ** throttle))
        return {
            "slot": self.KERNEL_ID,
            "nucleus": self.NUCLEUS,
            "status": "HALTED" if halted else "READY",
            "queue_depth": self._queue.qsize(),
            "queue_capacity": effective_capacity,
            "base_queue_capacity": self.queue_capacity,
            "inflight": inflight,
            "completed": completed,
            "failed": failed,
            "throttle_level": throttle,
            "last_latency_ms": latency,
        }

    def set_throttle(self, level: int) -> None:
        level = int(level)
        if level < 0 or level > 3:
            raise ValueError("G0 throttle must be in range 0..3")
        with self._lock:
            self._throttle = level

    def halt(self) -> None:
        with self._lock:
            self._halted = True

    def resume(self) -> None:
        with self._lock:
            self._halted = False

    def cycle(
        self,
        system: Any,
        input_text: str,
        *,
        cycle_id: str | None = None,
        context: dict[str, Any] | None = None,
        timeout_s: float = 120.0,
    ) -> Any:
        if system is None:
            raise RuntimeError("G0_SYSTEM_REQUIRED")
        if not isinstance(input_text, str) or not input_text.strip():
            raise ValueError("G0_INPUT_REQUIRED")
        if context is not None and not isinstance(context, dict):
            raise TypeError("G0_CONTEXT_MUST_BE_OBJECT")
        with self._lock:
            if self._halted:
                raise RuntimeError("G0_HALTED")
            throttle = self._throttle
        effective_capacity = max(1, self.queue_capacity // (2 ** throttle))
        if self._queue.qsize() >= effective_capacity:
            raise RuntimeError("G0_BACKPRESSURE")
        request = _CycleRequest(
            system=system,
            input_text=input_text,
            cycle_id=cycle_id,
            context=dict(context) if context is not None else None,
            done=Event(),
            queued_at=monotonic(),
        )
        try:
            self._queue.put_nowait(request)
        except Full as exc:
            raise RuntimeError("G0_BACKPRESSURE") from exc
        if not request.done.wait(timeout=max(0.1, float(timeout_s))):
            raise TimeoutError("G0_CYCLE_TIMEOUT")
        if request.error is not None:
            raise request.error
        return request.result

    def audit(self, ara_extended: Any, etr_extended: Any, input_text: str) -> dict[str, Any]:
        flaws = [
            *ara_extended.detect(input_text),
            *getattr(ara_extended, "detect_semantic", lambda _t: [])(input_text),
            *getattr(ara_extended, "detect_structural", lambda _t: [])(input_text),
            *getattr(ara_extended, "detect_relational", lambda _t: [])(input_text),
        ]
        ethical = etr_extended.validate_multi_framework(input_text)
        return {
            "operation": "audit",
            "count": len(flaws),
            "flaws": [getattr(flaw, "__dict__", str(flaw)) for flaw in flaws],
            "ethical": getattr(ethical, "__dict__", str(ethical)),
        }

    def regenerate(self, ara_extended: Any, etr_extended: Any, input_text: str) -> dict[str, Any]:
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
            "ethical": getattr(ethical, "__dict__", str(ethical)),
        }

    def state(self, system: Any) -> dict[str, Any]:
        return system.state()

    def trace(self, trace: Any, cycle_id: str) -> dict[str, Any]:
        if not cycle_id.strip():
            raise ValueError("G0_TRACE_CYCLE_ID_REQUIRED")
        entries = trace.query({"cycle_id": cycle_id})
        return {
            "cycle_id": cycle_id,
            "integrity": trace.verify(),
            "entries": [getattr(entry, "__dict__", str(entry)) for entry in entries],
        }

    def _run(self) -> None:
        while True:
            request = self._queue.get()
            if request is None:
                self._queue.task_done()
                return
            started = monotonic()
            with self._lock:
                self._inflight += 1
            try:
                request.result = request.system.process(
                    request.input_text,
                    cycle_id=request.cycle_id,
                    context=request.context,
                )
                with self._lock:
                    self._completed += 1
            except BaseException as exc:
                request.error = exc
                with self._lock:
                    self._failed += 1
            finally:
                with self._lock:
                    self._inflight = max(0, self._inflight - 1)
                    self._last_latency_ms = (monotonic() - started) * 1000
                request.done.set()
                self._queue.task_done()
