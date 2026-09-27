"""Asynchronous in-process control bus for SARA/ERU.

The bus is deterministic and dependency-free. External brokers remain explicit
adapters. Control metadata (message/correlation/priority/ttl) is carried on the
same event record; no second control plane is created.
"""
from __future__ import annotations

import asyncio
import inspect
import uuid
from datetime import datetime, timezone
from typing import Any, Callable

Subscriber = Callable[[dict[str, Any]], Any]


class VagusNerveBus:
    NAME = "VagusNerveBus"
    VERSION = "1.1"

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = {}
        self._history: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()

    def subscribe(self, event_type: str, callback: Subscriber) -> None:
        if not event_type:
            raise ValueError("event_type é obrigatório")
        if not callable(callback):
            raise TypeError("callback deve ser chamável")
        self._subscribers.setdefault(event_type, []).append(callback)

    def _build_event(
        self,
        source: str,
        target: str,
        event_type: str,
        payload: dict[str, Any],
        status: str,
        *,
        correlation_id: str | None = None,
        message_id: str | None = None,
        priority: int | None = None,
        ttl: int | None = None,
    ) -> dict[str, Any]:
        if not str(source).strip() or not str(target).strip():
            raise ValueError("source e target são obrigatórios")
        if not str(event_type).strip():
            raise ValueError("event_type é obrigatório")
        if not isinstance(payload, dict):
            raise TypeError("payload deve ser um objeto")
        if priority is not None and not 0 <= int(priority) <= 100:
            raise ValueError("priority deve estar entre 0 e 100")
        if ttl is not None and int(ttl) <= 0:
            raise ValueError("ttl deve ser positivo")
        return {
            "event_id": message_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_module": str(source),
            "target_module": str(target),
            "event_type": str(event_type),
            "payload": dict(payload),
            "status": str(status or "EXECUTE"),
            "correlation_id": correlation_id or str(uuid.uuid4()),
            "priority": int(priority) if priority is not None else None,
            "ttl": int(ttl) if ttl is not None else None,
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
    ) -> dict[str, Any]:
        event = self._build_event(
            source,
            target,
            event_type,
            payload,
            status,
            correlation_id=correlation_id,
            message_id=message_id,
            priority=priority,
            ttl=ttl,
        )
        async with self._lock:
            self._history.append(dict(event))
        for callback in tuple(self._subscribers.get(event_type, ())):
            result = callback(dict(event))
            if inspect.isawaitable(result):
                await result
        return dict(event)

    def publish_sync(
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
    ) -> dict[str, Any]:
        """Synchronous adapter for synchronous HTTP/control-plane callers."""
        try:
            asyncio.get_running_loop()
        except RuntimeError:
            return asyncio.run(
                self.publish(
                    source,
                    target,
                    event_type,
                    payload,
                    status,
                    correlation_id=correlation_id,
                    message_id=message_id,
                    priority=priority,
                    ttl=ttl,
                )
            )
        raise RuntimeError("publish_sync cannot run inside an active event loop")

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 0:
            raise ValueError("limit deve ser >= 0")
        return [dict(x) for x in self._history[-limit:]] if limit else []

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "backend": "in_process",
            "async": True,
            "history_events": len(self._history),
            "external_broker": False,
            "control_metadata": [
                "message_id",
                "correlation_id",
                "priority",
                "ttl",
            ],
        }
