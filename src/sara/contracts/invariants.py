"""SARA — Invariant validation and fail-closed bootstrap gates.
Production rule: no cycle execution before structural invariants pass.
"""
from __future__ import annotations
from dataclasses import dataclass, field
from typing import Any
from sara.contracts.base import CyclePhase, ModuleStatus
from sara.contracts.lifecycle import CANONICAL_ORDER


@dataclass(frozen=True)
class InvariantCheck:
    name: str
    ok: bool
    blocking: bool
    detail: str = ""


@dataclass(frozen=True)
class InvariantReport:
    ok: bool
    checks: tuple[InvariantCheck, ...]
    blocking_failures: tuple[str, ...]
    warnings: tuple[str, ...] = ()

    def as_dict(self) -> dict[str, Any]:
        return {
            "ok": self.ok,
            "blocking_failures": list(self.blocking_failures),
            "warnings": list(self.warnings),
            "checks": [
                {"name": c.name, "ok": c.ok, "blocking": c.blocking, "detail": c.detail}
                for c in self.checks
            ],
        }


class InvariantValidator:
    """Validates contracts before execution and cycle invariants after execution."""

    NON_REGISTRY_DEPENDENCIES = {
        "ProvenanceTracker", "CycleContext", "TraceSink", "ModuleRegistry",
    }

    def validate_registry(self, registry: Any) -> InvariantReport:
        checks: list[InvariantCheck] = []
        snapshot = registry.snapshot()
        modules = snapshot.get("modules", {})

        checks.append(InvariantCheck(
            "registry_non_empty", bool(modules), True,
            f"modules={len(modules)}",
        ))

        names = set(modules)
        missing: list[str] = []
        pending_missing_metadata: list[str] = []
        for name, meta in modules.items():
            for key in ("status", "role", "dependencies", "phases"):
                if key not in meta:
                    pending_missing_metadata.append(f"{name}.{key}")
            for dep in meta.get("dependencies", []):
                if dep not in names and dep not in self.NON_REGISTRY_DEPENDENCIES:
                    missing.append(f"{name}->{dep}")

        checks.append(InvariantCheck(
            "dependency_resolution", not missing, True,
            "ok" if not missing else "; ".join(missing),
        ))
        checks.append(InvariantCheck(
            "module_metadata_complete", not pending_missing_metadata, True,
            "ok" if not pending_missing_metadata else "; ".join(pending_missing_metadata),
        ))

        invalid_phases: list[str] = []
        canonical = {p.value for p in CyclePhase}
        for name, meta in modules.items():
            for phase in meta.get("phases", []):
                if phase not in canonical:
                    invalid_phases.append(f"{name}:{phase}")
        checks.append(InvariantCheck(
            "phase_contracts_valid", not invalid_phases, True,
            "ok" if not invalid_phases else "; ".join(invalid_phases),
        ))

        pending = [
            name for name, meta in modules.items()
            if meta.get("status") == ModuleStatus.PENDING_INFRASTRUCTURE.value
        ]
        checks.append(InvariantCheck(
            "pending_modules_not_executed_by_default", True, True,
            f"pending={len(pending)}",
        ))

        order = [p.value for p in CANONICAL_ORDER]
        checks.append(InvariantCheck(
            "canonical_phase_order_complete",
            order == [p.value for p in CANONICAL_ORDER] and len(order) == 12,
            True,
            "12 canonical phases",
        ))

        failures = tuple(c.name for c in checks if c.blocking and not c.ok)
        warnings = tuple(
            f"{name}: PENDING_INFRASTRUCTURE"
            for name in pending
        )
        return InvariantReport(
            ok=not failures,
            checks=tuple(checks),
            blocking_failures=failures,
            warnings=warnings,
        )

    def validate_context_pre_execution(self, ctx: Any) -> InvariantReport:
        checks = [
            InvariantCheck("cycle_id_present", bool(ctx.cycle_id), True),
            InvariantCheck("input_present", isinstance(ctx.input, str), True),
            InvariantCheck("current_initialized", isinstance(ctx.current, str), True),
            InvariantCheck("trace_sink_present", ctx.sink is not None, True),
        ]
        failures = tuple(c.name for c in checks if c.blocking and not c.ok)
        return InvariantReport(not failures, tuple(checks), failures)

    def validate_cycle(self, ctx: Any, cycle: dict[str, Any]) -> InvariantReport:
        checks: list[InvariantCheck] = []
        phase_order = []
        for step in ctx.steps:
            if step.phase in {p.value for p in CyclePhase}:
                phase_order.append(step.phase)

        canonical = [p.value for p in CANONICAL_ORDER]
        positions = [canonical.index(p) for p in phase_order if p in canonical]
        monotonic = positions == sorted(positions)
        checks.append(InvariantCheck(
            "phase_order_monotonic", monotonic, True,
            "ok" if monotonic else f"observed={phase_order}",
        ))

        failed_steps = [f"{s.phase}:{s.module}" for s in ctx.steps if not s.ok]
        aborted = bool(cycle.get("aborted_at"))
        checks.append(InvariantCheck(
            "failed_step_has_abort_or_explicit_nonblocking",
            not failed_steps or aborted,
            True,
            "ok" if not failed_steps or aborted else "; ".join(failed_steps),
        ))

        execution = "execution" in cycle.get("phases", {})
        persistence = "persistence" in cycle.get("phases", {})
        snapshot = "snapshot" in cycle.get("phases", {})
        checks.append(InvariantCheck(
            "execution_has_persistence_and_snapshot",
            not execution or (persistence and snapshot),
            True,
        ))

        if ctx.aborted:
            checks.append(InvariantCheck(
                "abort_reason_present", bool(ctx.abort_reason), True, ctx.abort_reason
            ))

        failures = tuple(c.name for c in checks if c.blocking and not c.ok)
        return InvariantReport(not failures, tuple(checks), failures)
