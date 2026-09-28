"""Canonical in-process Vagus control bus for SARA/ERU/Octacore.

The bus remains the control plane. It does not execute remote jobs or create a
second Mesh. It is safe for the threaded HTTP service and async callers.
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

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = {}
        self._history: list[dict[str, Any]] = []
        self._lock = threading.RLock()
        self._sequence = 0

    def subscribe(self, event_type: str, callback: Subscriber) -> None:
        event_type = str(event_type).strip()
        if not event_type:
            raise ValueError("event_type é obrigatório")
        if not callable(callback):
            raise TypeError("callback deve ser chamável")
        with self._lock:
            self._subscribers.setdefault(event_type, []).append(callback)

    def _build_event(
        self,
        source: str,
        target: str,
        event_type: str,
        payload: dict[str, Any],
        status: str = "EXECUTE",
        *,
        correlation_id: str | None = None,
        message_id: str | None = None,
        priority: int = 50,
        ttl: int = 30_000,
    ) -> dict[str, Any]:
        if not str(source).strip() or not str(target).strip():
            raise ValueError("source e target são obrigatórios")
        if not str(event_type).strip():
            raise ValueError("event_type é obrigatório")
        if not isinstance(payload, dict):
            raise TypeError("payload deve ser objeto")
        if not 0 <= int(priority) <= 100:
            raise ValueError("priority deve estar entre 0 e 100")
        if int(ttl) <= 0:
            raise ValueError("ttl deve ser positivo")
        correlation = str(correlation_id or "").strip() or str(uuid.uuid4())
        with self._lock:
            self._sequence += 1
            sequence = self._sequence
        return {
            "event_id": str(message_id or uuid.uuid4()),
            "sequence": sequence,
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_module": str(source),
            "target_module": str(target),
            "event_type": str(event_type),
            "payload": dict(payload),
            "status": str(status or "EXECUTE"),
            "correlation_id": correlation,
            "priority": int(priority),
            "ttl": int(ttl),
            "vagus_version": self.VERSION,
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
        priority: int = 50,
        ttl: int = 30_000,
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
        with self._lock:
            self._history.append(dict(event))
            callbacks = tuple(self._subscribers.get(event_type, ()))

        for callback in callbacks:
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
        priority: int = 50,
        ttl: int = 30_000,
    ) -> dict[str, Any]:
        """Thread-safe synchronous bridge used by the threaded HTTP service."""
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
        with self._lock:
            self._history.append(dict(event))
            callbacks = tuple(self._subscribers.get(event_type, ()))

        for callback in callbacks:
            result = callback(dict(event))
            if inspect.isawaitable(result):
                try:
                    asyncio.run(result)
                except RuntimeError as exc:
                    raise RuntimeError("VAGUS_ASYNC_CALLBACK_REQUIRES_ASYNC_PUBLISH") from exc
        return dict(event)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 0:
            raise ValueError("limit deve ser >= 0")
        with self._lock:
            items = self._history[-limit:] if limit else []
            return [dict(x) for x in items]

    def describe(self) -> dict[str, Any]:
        with self._lock:
            history_events = len(self._history)
            subscribers = sum(len(v) for v in self._subscribers.values())
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "backend": "in_process",
            "async": True,
            "thread_safe": True,
            "history_events": history_events,
            "subscribers": subscribers,
            "external_broker": False,
            "control_plane": True,
        }
