"""Asynchronous event bus for SARA/ERU.

The in-process backend is deterministic and dependency-free. Redis is optional:
when configured, callers may provide a real Redis transport; this module never
pretends that an external broker exists when it does not.
"""
from __future__ import annotations
import asyncio
import inspect
import threading
import uuid
from datetime import datetime, timezone
from typing import Any, Awaitable, Callable

Subscriber = Callable[[dict[str, Any]], Any]


class VagusNerveBus:
    NAME = "VagusNerveBus"
    VERSION = "1.0"

    def __init__(self) -> None:
        self._subscribers: dict[str, list[Subscriber]] = {}
        self._history: list[dict[str, Any]] = []
        self._lock = asyncio.Lock()
        self._history_lock = threading.RLock()

    def subscribe(self, event_type: str, callback: Subscriber) -> None:
        if not event_type:
            raise ValueError("event_type é obrigatório")
        self._subscribers.setdefault(event_type, []).append(callback)

    async def publish(
        self, source: str, target: str, event_type: str, payload: dict[str, Any],
        status: str = "EXECUTE",
        *,
        correlation_id: str | None = None,
        message_id: str | None = None,
        priority: int | None = None,
        ttl: int | None = None,
    ) -> dict[str, Any]:
        event = {
            "event_id": message_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_module": source,
            "target_module": target,
            "event_type": event_type,
            "payload": payload,
            "status": status,
            "correlation_id": correlation_id,
            "priority": priority,
            "ttl": ttl,
        }
        async with self._lock:
            with self._history_lock:
                self._history.append(event)
        for callback in tuple(self._subscribers.get(event_type, ())):
            result = callback(event)
            if inspect.isawaitable(result):
                await result
        return dict(event)


    def publish_sync(
        self, source: str, target: str, event_type: str, payload: dict[str, Any],
        status: str = "EXECUTE",
        *,
        correlation_id: str | None = None,
        message_id: str | None = None,
        priority: int | None = None,
        ttl: int | None = None,
    ) -> dict[str, Any]:
        """Synchronous bridge for thread-based HTTP handlers.
        It preserves the canonical event shape while avoiding an asyncio.Lock
        bound to a different event loop.
        """
        event = {
            "event_id": message_id or str(uuid.uuid4()),
            "timestamp": datetime.now(timezone.utc).isoformat(),
            "source_module": source,
            "target_module": target,
            "event_type": event_type,
            "payload": payload,
            "status": status,
            "correlation_id": correlation_id,
            "priority": priority,
            "ttl": ttl,
        }
        with self._history_lock:
            self._history.append(event)
        try:
            running_loop = asyncio.get_running_loop()
        except RuntimeError:
            running_loop = None

        for callback in tuple(self._subscribers.get(event_type, ())):
            result = callback(event)
            if inspect.isawaitable(result):
                if running_loop is not None:
                    running_loop.create_task(result)
                else:
                    asyncio.run(result)
        return dict(event)

    def get_history(self, limit: int = 50) -> list[dict[str, Any]]:
        if limit < 0:
            raise ValueError("limit deve ser >= 0")
        with self._history_lock:
            return [dict(x) for x in self._history[-limit:]] if limit else []

    def describe(self) -> dict[str, Any]:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "backend": "in_process",
            "async": True,
            "history_events": len(self._history),
            "external_broker": False,
        }
