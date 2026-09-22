"""Bounded working-memory layer for SARA/ERU."""
from __future__ import annotations
import copy
from collections import deque
from typing import Any


class WorkingMemory:
    NAME = "WorkingMemory"
    VERSION = "1.0"

    def __init__(self, max_items: int = 256) -> None:
        if max_items < 1:
            raise ValueError("max_items deve ser >= 1")
        self._items: deque[dict[str, Any]] = deque(maxlen=max_items)

    def put(self, key: str, value: Any) -> None:
        if not key:
            raise ValueError("key é obrigatório")
        self._items.append({"key": key, "value": copy.deepcopy(value)})

    def get(self, key: str) -> Any:
        for item in reversed(self._items):
            if item["key"] == key:
                return copy.deepcopy(item["value"])
        return None

    def snapshot(self) -> list[dict[str, Any]]:
        return copy.deepcopy(list(self._items))

    def describe(self) -> dict[str, Any]:
        return {"name": self.NAME, "version": self.VERSION, "items": len(self._items)}
