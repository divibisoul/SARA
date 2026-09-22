"""SARA — ModuleRegistry.
Status: IMPLEMENTED (foundational).
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any
from sara.contracts.base import (
    SaraModule, ModuleStatus, CycleRole, CyclePhase,
)


class RegistryError(Exception):
    pass


@dataclass
class RegisteredModule:
    name: str
    instance: Any
    status: ModuleStatus
    role: CycleRole
    dependencies: tuple[str, ...]
    phases: tuple[CyclePhase, ...]


class ModuleRegistry:
    def __init__(self) -> None:
        self._modules: dict[str, RegisteredModule] = {}

    def register(self, instance: Any) -> RegisteredModule:
        if not isinstance(instance, SaraModule):
            raise RegistryError(
                f"objeto '{type(instance).__name__}' não satisfaz o protocolo SaraModule"
            )
        name = instance.NAME
        if name in self._modules:
            raise RegistryError(f"módulo '{name}' já registrado")
        entry = RegisteredModule(
            name=name,
            instance=instance,
            status=instance.STATUS,
            role=instance.ROLE,
            dependencies=instance.DEPENDENCIES,
            phases=instance.CYCLE_PHASES,
        )
        self._modules[name] = entry
        return entry

    def validate_dependencies(self) -> list[str]:
        missing: list[str] = []
        for name, entry in self._modules.items():
            for dep in entry.dependencies:
                if dep not in self._modules:
                    missing.append(f"{name} → {dep}")
        return missing

    def modules_for_phase(self, phase: CyclePhase) -> list[RegisteredModule]:
        return [m for m in self._modules.values() if phase in m.phases]

    def by_status(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {s.value: [] for s in ModuleStatus}
        for m in self._modules.values():
            out[m.status.value].append(m.name)
        return out

    def snapshot(self) -> dict:
        return {
            "count": len(self._modules),
            "by_status": self.by_status(),
            "modules": {
                name: {
                    "status": m.status.value,
                    "role": m.role.value,
                    "dependencies": list(m.dependencies),
                    "phases": [p.value for p in m.phases],
                }
                for name, m in self._modules.items()
            },
        }