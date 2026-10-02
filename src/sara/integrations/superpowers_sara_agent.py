"""Explicit Superpowers bridge for the SARA regenerative chain.

Superpowers remains an upstream methodology/skills source. This adapter binds one
SARA-local agent boundary to ARA/ETR/ITR/RGO/MMD without creating a second authority.
It never reports runtime success for an unavailable external harness.
"""
from __future__ import annotations
from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class SuperpowersSaraAgent:
    name: str = "superpowers.sara-trinity"
    upstream: str = "https://github.com/obra/superpowers"
    revision: str = "8ca22dba9a94f28898bbce59f2537ff4d87c747d"
    targets: tuple[str, ...] = ("ARA", "ETR", "ITR", "RGO", "MMD")
    skills: tuple[str, ...] = (
        "brainstorming",
        "writing-plans",
        "subagent-driven-development",
        "test-driven-development",
        "systematic-debugging",
        "requesting-code-review",
        "verification-before-completion",
    )

    def bind(self, *, ara: Any, etr: Any, itr: Any, rgo: Any, mmd: Any) -> None:
        objects = {"ARA": ara, "ETR": etr, "ITR": itr, "RGO": rgo, "MMD": mmd}
        missing = [name for name, value in objects.items() if value is None]
        if missing:
            raise ValueError("SUPERPOWERS_SARA_BINDING_MISSING:" + ",".join(missing))
        object.__setattr__(self, "_bindings", objects)

    def describe(self) -> dict[str, Any]:
        bindings = getattr(self, "_bindings", {})
        return {
            "name": self.name,
            "status": "BOUND" if len(bindings) == len(self.targets) else "UNBOUND",
            "upstream": self.upstream,
            "revision": self.revision,
            "targets": list(self.targets),
            "skills": list(self.skills),
            "bound_targets": sorted(bindings),
            "authority": "SARA",
            "runtime_activation_requires_explicit_adapter": True,
            "no_fake_runtime_success": True,
        }

    def prepare(self, target: str, operation: str, *, evidence: dict[str, Any]) -> dict[str, Any]:
        if target not in self.targets:
            raise ValueError(f"SUPERPOWERS_SARA_TARGET_NOT_BOUND:{target}")
        if not isinstance(evidence, dict) or not evidence:
            raise ValueError("SUPERPOWERS_SARA_EVIDENCE_REQUIRED")
        return {
            "agent": self.name,
            "target": target,
            "operation": operation,
            "skills": list(self.skills),
            "evidence": dict(evidence),
            "authority": "SARA",
        }
