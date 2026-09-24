"""VagusBus — transversal communication/control plane for SARA.

The bus is intentionally in-process and evidence-honest: it never claims an
external broker, durable delivery, or distributed connectivity that was not
actually configured and exercised.

The event envelope keeps SARA's legacy fields while also exposing the core
CloudEvents 1.0 identity fields and correlation metadata.  This lets the bus
grow toward distributed federation without changing existing producers.
"""
from __future__ import annotations

import asyncio
import inspect
import threading
import uuid
from functools import wraps
from datetime import datetime, timezone
from typing import Any, Callable

Subscriber = Callable[[dict[str, Any]], Any]


class VagusNerveBus:
    NAME = "VagusNerveBus"
    VERSION = "1.1"
    EVENT_SPECVERSION = "1.0"

    def __init__(self) -> None:
        self._subscribers: dict[tuple[str, str | None], list[Subscriber]] = {}
        self._history: list[dict[str, Any]] = []
        self._modules: dict[str, dict[str, Any]] = {}
        self._history_lock = threading.RLock()

    def subscribe(
        self,
        event_type: str,
        callback: Subscriber,
        *,
        target: str | None = None,
    ) -> None:
        if not event_type:
            raise ValueError("event_type é obrigatório")
        key = (event_type, target)
        self._subscribers.setdefault(key, []).append(callback)

    def register_module(self, module: Any, *, emit: bool = True) -> dict[str, Any]:
        name = str(getattr(module, "NAME", type(module).__name__))
        binding = {
            "name": name,
            "version": str(getattr(module, "VERSION", "unknown")),
            "status": getattr(getattr(module, "STATUS", None), "value", str(getattr(module, "STATUS", "unknown"))),
            "role": getattr(getattr(module, "ROLE", None), "value", str(getattr(module, "ROLE", "unknown"))),
            "dependencies": list(getattr(module, "DEPENDENCIES", ())),
            "phases": [
                getattr(phase, "value", str(phase))
                for phase in getattr(module, "CYCLE_PHASES", ())
            ],
        }
        try:
            setattr(module, "_vagus_bus", self)
            self.instrument_module(module)
            binding["runtime_bound"] = getattr(module, "_vagus_bus", None) is self
            binding["instrumented"] = True
            binding["runtime_binding_error"] = None
        except Exception as exc:
            binding["runtime_bound"] = False
            binding["instrumented"] = False
            binding["runtime_binding_error"] = f"{type(exc).__name__}: {exc}"
        with self._history_lock:
            self._modules[name] = dict(binding)
        if emit:
            self.publish_sync(
                "urn:sara:vagus",
                name,
                "module.registered",
                {"module": binding},
                status="CONNECTED" if binding["runtime_bound"] else "BLOCKED",
                correlation_id=f"module:{name}",
                priority=100,
                ttl=0,
            )
        return dict(binding)

    _INSTRUMENTATION_EXCLUDE = frozenset({
        "describe", "emit_trace", "provenance", "module_bindings",
        "get_history", "last_actions",
    })

    def instrument_module(self, module: Any) -> None:
        """Instrument public operational methods without replacing their bodies."""
        if getattr(module, "_vagus_instrumented", False):
            return
        instrumented: set[str] = set()
        for name in dir(module):
            if name.startswith("_") or name in self._INSTRUMENTATION_EXCLUDE:
                continue
            try:
                original = getattr(module, name)
            except Exception:
                continue
            if not callable(original) or getattr(original, "_vagus_wrapper", False):
                continue

            if inspect.iscoroutinefunction(original):
                @wraps(original)
                async def async_wrapper(*args: Any, __original=original, __name=name, **kwargs: Any) -> Any:
                    correlation = self._correlation_from(args, kwargs)
                    self.publish_sync(
                        str(getattr(module, "NAME", type(module).__name__)),
                        str(getattr(module, "NAME", type(module).__name__)),
                        "module.method.start",
                        {"method": __name},
                        status="EXECUTE",
                        correlation_id=correlation,
                    )
                    try:
                        result = await __original(*args, **kwargs)
                    except Exception as exc:
                        self.publish_sync(
                            str(getattr(module, "NAME", type(module).__name__)),
                            str(getattr(module, "NAME", type(module).__name__)),
                            "module.method.error",
                            {"method": __name, "error": type(exc).__name__},
                            status="ERROR",
                            correlation_id=correlation,
                        )
                        raise
                    self.publish_sync(
                        str(getattr(module, "NAME", type(module).__name__)),
                        str(getattr(module, "NAME", type(module).__name__)),
                        "module.method.complete",
                        {"method": __name, "result_type": type(result).__name__},
                        status="RESULT",
                        correlation_id=correlation,
                    )
                    return result
                async_wrapper._vagus_wrapper = True  # type: ignore[attr-defined]
                setattr(module, name, async_wrapper)
            else:
                @wraps(original)
                def sync_wrapper(*args: Any, __original=original, __name=name, **kwargs: Any) -> Any:
                    correlation = self._correlation_from(args, kwargs)
                    self.publish_sync(
                        str(getattr(module, "NAME", type(module).__name__)),
                        str(getattr(module, "NAME", type(module).__name__)),
                        "module.method.start",
                        {"method": __name},
                        status="EXECUTE",
                        correlation_id=correlation,
                    )
                    try:
                        result = __original(*args, **kwargs)
                    except Exception as exc:
                        self.publish_sync(
                            str(getattr(module, "NAME", type(module).__name__)),
                            str(getattr(module, "NAME", type(module).__name__)),
                            "module.method.error",
                            {"method": __name, "error": type(exc).__name__},
                            status="ERROR",
                            correlation_id=correlation,
                        )
                        raise
                    self.publish_sync(
                        str(getattr(module, "NAME", type(module).__name__)),
                        str(getattr(module, "NAME", type(module).__name__)),
                        "module.method.complete",
                        {"method": __name, "result_type": type(result).__name__},
                        status="RESULT",
                        correlation_id=correlation,
                    )
                    return result
                sync_wrapper._vagus_wrapper = True  # type: ignore[attr-defined]
                setattr(module, name, sync_wrapper)
            instrumented.add(name)
        setattr(module, "_vagus_instrumented", True)
        setattr(module, "_vagus_instrumented_methods", tuple(sorted(instrumented)))

    @staticmethod
    def _correlation_from(args: tuple[Any, ...], kwargs: dict[str, Any]) -> str | None:
        for value in (*args, *kwargs.values()):
            candidate = getattr(value, "cycle_id", None)
            if candidate:
                return str(candidate)
        for key in ("correlation_id", "cycle_id", "trace_id"):
            value = kwargs.get(key)
            if value:
                return str(value)
        return None

    def emit_module_event(
        self,
        module: Any,
        event_type: str,
        payload: dict[str, Any],
        *,
        target: str | None = None,
        status: str = "EXECUTE",
        correlation_id: str | None = None,
        trace_id: str | None = None,
        causation_id: str | None = None,
        phase: str | None = None,
        provenance: str | None = None,
        priority: int | None = None,
        ttl: int | None = None,
    ) -> dict[str, Any]:
        """Emit an event using an already-bound SARA module identity."""
        source = str(getattr(module, "NAME", type(module).__name__))
        destination = target or source
        return self.publish_sync(
            source,
            destination,
            event_type,
            payload,
            status=status,
            correlation_id=correlation_id,
            trace_id=trace_id,
            causation_id=causation_id,
            phase=phase,
            provenance=provenance,
            priority=priority,
            ttl=ttl,
        )

    def bind_registry(self, registry: Any) -> dict[str, Any]:
        """Bind every registered SARA module to the Vagus control plane.

        This is an additive control-plane binding: it does not replace module
        contracts, dependencies, or ownership. It records the actual inventory
        and emits one registration event per module.
        """
        entries = list(registry.items())
        bindings = [self.register_module(entry.instance) for entry in entries]
        return {
            "status": "VERIFIED",
            "module_count": len(bindings),
            "bound_modules": [b["name"] for b in bindings],
        }

    def forensic_audit(self, registry: Any) -> dict[str, Any]:
        """Run the transversal structural audit without executing mutations."""
        entries = list(registry.items())
        inventory = {
            "count": len(entries),
            "names": [entry.name for entry in entries],
        }
        contract_failures: list[dict[str, str]] = []
        for entry in entries:
            module = entry.instance
            for attr in ("NAME", "VERSION", "STATUS", "ROLE", "DEPENDENCIES", "CYCLE_PHASES", "describe"):
                if not hasattr(module, attr):
                    contract_failures.append({"module": entry.name, "missing": attr})
            try:
                description = module.describe()
                if not isinstance(description, dict):
                    contract_failures.append({"module": entry.name, "reason": "describe() não retorna dict"})
            except Exception as exc:
                contract_failures.append({
                    "module": entry.name,
                    "reason": f"describe() falhou: {type(exc).__name__}: {exc}",
                })

        description_mismatches: list[dict[str, Any]] = []
        for entry in entries:
            module = entry.instance
            try:
                description = module.describe()
                expected = {
                    "name": str(getattr(module, "NAME")),
                    "version": str(getattr(module, "VERSION")),
                    "status": getattr(getattr(module, "STATUS"), "value", str(getattr(module, "STATUS"))),
                    "role": getattr(getattr(module, "ROLE"), "value", str(getattr(module, "ROLE"))),
                    "dependencies": list(getattr(module, "DEPENDENCIES")),
                    "phases": [
                        getattr(phase, "value", str(phase))
                        for phase in getattr(module, "CYCLE_PHASES")
                    ],
                }
                for key, expected_value in expected.items():
                    if key in description and description[key] != expected_value:
                        description_mismatches.append({
                            "module": entry.name,
                            "field": key,
                            "expected": expected_value,
                            "reported": description[key],
                        })
            except Exception:
                # A contract failure was already recorded above; avoid duplicating
                # the same exception in the consistency section.
                continue

        dependency_failures = list(registry.validate_dependencies())
        try:
            dependency_order = registry.dependency_order()
            dependency_cycle = False
        except Exception as exc:
            dependency_order = []
            dependency_cycle = True
            dependency_failures.append(str(exc))

        with self._history_lock:
            bound_names = set(self._modules)
            registration_events = {
                str(event.get("target_module"))
                for event in self._history
                if event.get("event_type") == "module.registered"
            }

        unbound = sorted(set(inventory["names"]) - bound_names)
        runtime_unbound = sorted(
            name for name, binding in self._modules.items()
            if not bool(binding.get("runtime_bound"))
        )
        missing_evidence = sorted(set(inventory["names"]) - registration_events)
        structural_ok = (not contract_failures and not description_mismatches
                         and not dependency_failures and not unbound
                         and not missing_evidence and not dependency_cycle and not runtime_unbound\n                         and not any(not b.get("instrumented") for b in self._modules.values()))

        return {
            "status": "VERIFIED" if structural_ok else "BLOCKED",
            "scope": "STRUCTURAL_TRANSVERSAL",
            "inventory": inventory,
            "contract_failures": contract_failures,
            "description_mismatches": description_mismatches,
            "dependency_failures": dependency_failures,
            "dependency_order": dependency_order,
            "vagus_unbound_modules": unbound,
            "vagus_missing_registration_evidence": missing_evidence,
            "vagus_runtime_unbound_modules": runtime_unbound,
            "vagus_non_instrumented_modules": sorted(name for name, binding in self._modules.items() if not binding.get("instrumented")),
            "functional_execution": "UNMEASURABLE",
            "external_broker": "UNMEASURABLE",
        }

    async def publish(
        self,
        source: str,
        target: str,
        event_type: str,
        payload: dict[str, Any],
        status: str = "EXECUTE",
        *,
        correlation_id: str | None = None,
        message_id: str | None = None,
        priority: int | None = None,
        ttl: int | None = None,
        trace_id: str | None = None,
        causation_id: str | None = None,
        phase: str | None = None,
        provenance: str | None = None,
    ) -> dict[str, Any]:
        event = self._publish(
            source, target, event_type, payload, status,
            correlation_id=correlation_id, message_id=message_id,
            priority=priority, ttl=ttl, trace_id=trace_id,
            causation_id=causation_id, phase=phase, provenance=provenance,
        )
        await self._dispatch_async(event)
        return dict(event)

    async def publish_async(
        self, source: str, target: str, event_type: str, payload: dict[str, Any],
        status: str = "EXECUTE", **kwargs: Any,
    ) -> dict[str, Any]:
        event = self._publish(source, target, event_type, payload, status, **kwargs)
        await self._dispatch_async(event)
        return dict(event)

    async def publish_legacy_async(
        self, source: str, target: str, event_type: str, payload: dict[str, Any],
        status: str = "EXECUTE", **kwargs: Any,
    ) -> dict[str, Any]:
        """Compatibility name for callers that used the old async publish API."""
        return await self.publish_async(
            source, target, event_type, payload, status, **kwargs
        )

    def publish_sync(
        self, source: str, target: str, event_type: str, payload: dict[str, Any],
        status: str = "EXECUTE",
        *,
        correlation_id: str | None = None,
        message_id: str | None = None,
        priority: int | None = None,
        ttl: int | None = None,
        trace_id: str | None = None,
        causation_id: str | None = None,
        phase: str | None = None,
        provenance: str | None = None,
    ) -> dict[str, Any]:
        event = self._publish(
            source, target, event_type, payload, status,
            correlation_id=correlation_id, message_id=message_id,
            priority=priority, ttl=ttl, trace_id=trace_id,
            causation_id=causation_id, phase=phase, provenance=provenance,
        )
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        for callback in self._callbacks_for(event):
            result = callback(event)
            if inspect.isawaitable(result):
                if running_loop is not None:
                    running_loop.create_task(result)
                else:
                    asyncio.run(result)
        return dict(event)

    def ack(self, message_id: str, consumer: str, *, correlation_id: str | None = None) -> dict[str, Any]:
        if not message_id or not consumer:
            raise ValueError("message_id e consumer são obrigatórios")
        return self.publish_sync(
            consumer,
            "urn:sara:vagus",
            "message.ack",
            {"message_id": message_id, "consumer": consumer},
            status="ACK",
            correlation_id=correlation_id or message_id,
            priority=100,
            ttl=0,
        )

    def replay(
        self,
        *,
        event_type: str | None = None,
        correlation_id: str | None = None,
        target: str | None = None,
        limit: int = 50,
    ) -> list[dict[str, Any]]:
        if limit < 0:
            raise ValueError("limit deve ser >= 0")
        with self._history_lock:
            events = list(self._history)
        filtered = [
            event for event in events
            if (event_type is None or event.get("event_type") == event_type)
            and (correlation_id is None or event.get("correlation_id") == correlation_id)
            and (target is None or event.get("target_module") == target)
        ]
        return [dict(event) for event in filtered[-limit:]] if limit else []

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        return self.replay(limit=limit)

    def describe(self) -> dict[str, Any]:
        with self._history_lock:
            history_events = len(self._history)
            module_count = len(self._modules)
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "event_specversion": self.EVENT_SPECVERSION,
            "backend": "in_process",
            "async": True,
            "history_events": history_events,
            "bound_modules": module_count,
            "external_broker": False,
            "delivery_guarantee": "in_process_best_effort",
        }

    def module_bindings(self) -> dict[str, dict[str, Any]]:
        with self._history_lock:
            return {name: dict(binding) for name, binding in self._modules.items()}

    def _publish(
        self, source: str, target: str, event_type: str, payload: dict[str, Any],
        status: str,
        *,
        correlation_id: str | None,
        message_id: str | None,
        priority: int | None,
        ttl: int | None,
        trace_id: str | None,
        causation_id: str | None,
        phase: str | None,
        provenance: str | None,
    ) -> dict[str, Any]:
        if not source or not target or not event_type:
            raise ValueError("source, target e event_type são obrigatórios")
        if not isinstance(payload, dict):
            raise TypeError("payload deve ser dict")
        timestamp = datetime.now(timezone.utc).isoformat()
        event_id = message_id or str(uuid.uuid4())
        event = {
            # CloudEvents-compatible core identity.
            "specversion": self.EVENT_SPECVERSION,
            "id": event_id,
            "source": source if "://" in source or source.startswith(("urn:", "/")) else f"urn:sara:module:{source}",
            "type": event_type,
            "subject": target,
            "time": timestamp,
            "data": dict(payload),
            # SARA legacy contract retained additively.
            "event_id": event_id,
            "timestamp": timestamp,
            "source_module": source,
            "target_module": target,
            "event_type": event_type,
            "payload": dict(payload),
            "status": status,
            "correlation_id": correlation_id,
            "trace_id": trace_id,
            "causation_id": causation_id,
            "phase": phase,
            "provenance": provenance,
            "priority": priority,
            "ttl": ttl,
        }
        with self._history_lock:
            self._history.append(event)
        return event

    def _callbacks_for(self, event: dict[str, Any]) -> tuple[Subscriber, ...]:
        event_type = str(event["event_type"])
        target = str(event["target_module"])
        callbacks = [
            *self._subscribers.get((event_type, None), ()),
            *self._subscribers.get((event_type, target), ()),
        ]
        return tuple(callbacks)

    async def _dispatch_async(self, event: dict[str, Any]) -> None:
        for callback in self._callbacks_for(event):
            result = callback(event)
            if inspect.isawaitable(result):
                await result
