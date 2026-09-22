"""Bounded working-memory layer for SARA/ERU."""
from __future__ import annotations
import copy
from collections import deque
from typing import Any
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


class WorkingMemory:
    NAME = "WorkingMemory"
    VERSION = "1.1"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.MEMORY
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.PERSISTENCE,)

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
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "layer": "working_memory",
            "storage_scope": "process_ram_bounded",
            "items": len(self._items),
        }

    def emit_trace(self, ctx: Any) -> None:
        if hasattr(ctx, "record"):
            ctx.record(
                CyclePhase.PERSISTENCE.value,
                self.NAME,
                True,
                layer="working_memory",
                storage_scope="process_ram_bounded",
                items=len(self._items),
            )
