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
            binding["runtime_bound"] = getattr(module, "_vagus_bus", None) is self
            binding["runtime_binding_error"] = None
        except Exception as exc:
            binding["runtime_bound"] = False
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
        structural_ok = (not contract_failures and not dependency_failures and not unbound\n                         and not missing_evidence and not dependency_cycle and not runtime_unbound)\n
        return {
            "status": "VERIFIED" if structural_ok else "BLOCKED",
            "scope": "STRUCTURAL_TRANSVERSAL",
            "inventory": inventory,
            "contract_failures": contract_failures,
            "dependency_failures": dependency_failures,
            "dependency_order": dependency_order,
            "vagus_unbound_modules": unbound,
            "vagus_missing_registration_evidence": missing_evidence,\n            "vagus_runtime_unbound_modules": runtime_unbound,\n            "functional_execution": "UNMEASURABLE",
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
