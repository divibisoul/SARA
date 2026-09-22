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

    EXTERNAL_RUNTIME_DEPENDENCIES = {
        "ProvenanceTracker", "CycleContext", "TraceSink", "ModuleRegistry",
    }

    def validate_dependencies(self) -> list[str]:
        """Valida apenas dependências que devem existir no registry.

        Alguns contratos representam infraestrutura/contexto de runtime e não
        são módulos registráveis; eles permanecem explicitamente permitidos.
        """
        missing: list[str] = []
        for name, entry in self._modules.items():
            for dep in entry.dependencies:
                if (
                    dep not in self._modules
                    and dep not in self.EXTERNAL_RUNTIME_DEPENDENCIES
                ):
                    missing.append(f"{name} → {dep}")
        return missing

    def modules_for_phase(self, phase: CyclePhase) -> list[RegisteredModule]:
        return [m for m in self._modules.values() if phase in m.phases]

    def by_status(self) -> dict[str, list[str]]:
        out: dict[str, list[str]] = {s.value: [] for s in ModuleStatus}
        for m in self._modules.values():
            out[m.status.value].append(m.name)
        return out

    def get(self, name: str) -> RegisteredModule | None:
        """Retorna um módulo registrado sem expor o dicionário interno."""
        return self._modules.get(name)

    def items(self) -> list[RegisteredModule]:
        """Snapshot imutável da coleção de módulos registrados."""
        return list(self._modules.values())

    def dependency_order(self) -> list[str]:
        """Retorna ordem topológica determinística do grafo de módulos."""
        names = set(self._modules)
        deps = {
            name: {d for d in entry.dependencies if d in names}
            for name, entry in self._modules.items()
        }
        indegree = {name: len(values) for name, values in deps.items()}
        dependents: dict[str, set[str]] = {name: set() for name in names}
        for name, values in deps.items():
            for dep in values:
                dependents[dep].add(name)

        ready = sorted(name for name, degree in indegree.items() if degree == 0)
        order: list[str] = []
        while ready:
            name = ready.pop(0)
            order.append(name)
            for child in sorted(dependents[name]):
                indegree[child] -= 1
                if indegree[child] == 0:
                    ready.append(child)
                    ready.sort()

        if len(order) != len(names):
            cyclic = sorted(names - set(order))
            raise RegistryError(
                "ciclo de dependências detectado: " + ", ".join(cyclic)
            )
        return order

    def dependency_graph(self) -> dict[str, list[str]]:
        return {
            name: list(entry.dependencies)
            for name, entry in self._modules.items()
        }

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