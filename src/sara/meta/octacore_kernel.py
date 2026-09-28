"""G0 kernel for the Octacore system processor.

This is an additive execution boundary over the existing SARA runtime. It does
not implement a second ARA/ETR/ITR path and never substitutes for SARA.
"""
from __future__ import annotations

from dataclasses import dataclass
from queue import Full, Queue
from threading import Event, Lock, RLock, Thread
from time import monotonic
from typing import Any

from sara.contracts.base import CyclePhase, CycleRole, ModuleStatus


@dataclass
class _CycleRequest:
    input_text: str
    cycle_id: str | None
    context: dict[str, Any] | None
    done: Event
    result: Any = None
    error: BaseException | None = None
    cancelled: Event | None = None


class OctacoreG0Kernel:
    NAME = "OctacoreG0Kernel"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES = (
        "SistemaVivo",
        "RegenerativeLoop",
        "ARA_Extended",
        "ETR_Extended",
        "ITR_Extended",
        "DecisionTrace",
        "ProvenanceTracker",
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

    def __init__(self, *, queue_capacity: int = 32, cycle_timeout_s: float = 120.0) -> None:
        if queue_capacity <= 0:
            raise ValueError("queue_capacity must be positive")
        if cycle_timeout_s <= 0:
            raise ValueError("cycle_timeout_s must be positive")
        self._queue = Queue(maxsize=queue_capacity)
        self._queue_capacity = queue_capacity
        self._cycle_timeout_s = cycle_timeout_s
        self._state_lock = Lock()
        self._authority_lock = RLock()
        self._system = None
        self._halted = False
        self._throttle = 0
        self._inflight = 0
        self._completed = 0
        self._failed = 0
        self._last_latency_ms = 0
        self._worker = Thread(target=self._worker_loop, name="sara-octacore-g0", daemon=True)
        self._worker.start()

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "slot": self.KERNEL_ID,
            "nucleus": self.NUCLEUS,
            "type": "system_gpu_regenerative_kernel",
            "silicon_gpu": False,
            "authoritative": True,
            "capabilities": list(self.CAPABILITIES),
            "queue_capacity": self._queue_capacity,
            "cycle_timeout_s": self._cycle_timeout_s,
            "dependencies": list(self.DEPENDENCIES),
        }

    def health(self) -> dict[str, Any]:
        with self._state_lock:
            return {
                "slot": self.KERNEL_ID,
                "nucleus": self.NUCLEUS,
                "status": "HALTED" if self._halted else ("READY" if self._system is not None else "UNBOUND"),
                "queue_depth": self._queue.qsize(),
                "queue_capacity": self._effective_capacity(),
                "base_queue_capacity": self._queue_capacity,
                "inflight": self._inflight,
                "completed": self._completed,
                "failed": self._failed,
                "throttle_level": self._throttle,
                "last_latency_ms": self._last_latency_ms,
            }

    def bind(self, sistema_vivo: Any) -> "OctacoreG0Kernel":
        if sistema_vivo is None:
            raise ValueError("SistemaVivo is required")
        with self._state_lock:
            self._system = sistema_vivo
        return self

    def set_throttle(self, level: int) -> None:
        if level < 0 or level > 3:
            raise ValueError("G0 throttle level must be between 0 and 3")
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
        input_text: str,
        *,
        cycle_id: str | None = None,
        context: dict[str, Any] | None = None,
    ) -> Any:
        if not isinstance(input_text, str) or not input_text.strip():
            raise ValueError("G0_INPUT_REQUIRED")
        if context is not None and not isinstance(context, dict):
            raise TypeError("G0_CONTEXT_MUST_BE_OBJECT")
        with self._state_lock:
            if self._halted:
                raise RuntimeError("G0_HALTED")
            if self._system is None:
                raise RuntimeError("G0_UNBOUND")
        if self._queue.qsize() >= self._effective_capacity():
            raise RuntimeError("G0_BACKPRESSURE")
        request = _CycleRequest(
            input_text=input_text,
            cycle_id=cycle_id,
            context=dict(context) if context is not None else None,
            done=Event(),
            cancelled=Event(),
        )
        try:
            self._queue.put_nowait(request)
        except Full as exc:
            raise RuntimeError("G0_BACKPRESSURE") from exc
        if not request.done.wait(timeout=self._cycle_timeout_s):
            if request.cancelled is not None:
                request.cancelled.set()
            raise TimeoutError("G0_CYCLE_TIMEOUT")
        if request.error is not None:
            raise request.error
        return request.result

    def audit(self, ara: Any, etr: Any, input_text: str) -> dict[str, Any]:
        with self._authority_lock:
            return self._audit_locked(ara, etr, input_text)

    def _audit_locked(self, ara: Any, etr: Any, input_text: str) -> dict[str, Any]:
        flaws = [
            *ara.detect(input_text),
            *getattr(ara, "detect_semantic", lambda _text: [])(input_text),
            *getattr(ara, "detect_structural", lambda _text: [])(input_text),
            *getattr(ara, "detect_relational", lambda _text: [])(input_text),
        ]
        ethical = etr.validate_multi_framework(input_text)
        return {
            "operation": "audit",
            "flaws": [getattr(item, "__dict__", str(item)) for item in flaws],
            "count": len(flaws),
            "ethical": getattr(ethical, "__dict__", str(ethical)),
        }

    def regenerate(self, ara: Any, etr: Any, input_text: str) -> dict[str, Any]:
        with self._authority_lock:
            return self._regenerate_locked(ara, etr, input_text)

    def _regenerate_locked(self, ara: Any, etr: Any, input_text: str) -> dict[str, Any]:
        flaws = [
            *ara.detect(input_text),
            *getattr(ara, "detect_semantic", lambda _text: [])(input_text),
            *getattr(ara, "detect_structural", lambda _text: [])(input_text),
            *getattr(ara, "detect_relational", lambda _text: [])(input_text),
        ]
        regenerated = (
            ara.regenerate_semantic(input_text, flaws)
            if hasattr(ara, "regenerate_semantic")
            else ara.regenerate(input_text, flaws)
        )
        ethical = etr.validate_multi_framework(regenerated.transformed)
        return {
            "operation": "regenerate",
            "original": regenerated.original,
            "transformed": regenerated.transformed,
            "applied_rules": list(regenerated.applied_rules),
            "plan_steps": list(regenerated.plan_steps),
            "integrity_hash": regenerated.integrity_hash,
            "ethical": getattr(ethical, "__dict__", str(ethical)),
        }

    def state(self) -> dict[str, Any]:
        with self._state_lock:
            system = self._system
        if system is None:
            raise RuntimeError("G0_UNBOUND")
        return system.state()

    def trace(self, trace: Any, cycle_id: str) -> dict[str, Any]:
        cycle_id = str(cycle_id or "").strip()
        if not cycle_id:
            raise ValueError("G0_CYCLE_ID_REQUIRED")
        entries = trace.query({"cycle_id": cycle_id})
        return {
            "cycle_id": cycle_id,
            "integrity": trace.verify(),
            "entries": [getattr(entry, "__dict__", str(entry)) for entry in entries],
        }

    def _effective_capacity(self) -> int:
        with self._state_lock:
            return max(1, self._queue_capacity // (2 ** self._throttle))

    def _worker_loop(self) -> None:
        while True:
            request = self._queue.get()
            started = monotonic()
            with self._state_lock:
                self._inflight += 1
            try:
                with self._state_lock:
                    system = self._system
                    halted = self._halted
                if halted:
                    raise RuntimeError("G0_HALTED")
                if system is None:
                    raise RuntimeError("G0_UNBOUND")
                if request.cancelled is not None and request.cancelled.is_set():
                    raise RuntimeError("G0_CYCLE_CANCELLED")
                with self._authority_lock:
                    request.result = system.process(
                        request.input_text,
                        cycle_id=request.cycle_id,
                        context=request.context,
                    )
                with self._state_lock:
                    self._completed += 1
            except BaseException as exc:
                request.error = exc
                with self._state_lock:
                    self._failed += 1
            finally:
                elapsed = int((monotonic() - started) * 1000)
                with self._state_lock:
                    self._inflight = max(0, self._inflight - 1)
                    self._last_latency_ms = elapsed
                request.done.set()
                self._queue.task_done()
