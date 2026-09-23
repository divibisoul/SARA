"""SARA — Connected Runtime v1.0.

Camada de integração real entre os módulos existentes.
Não substitui nenhum núcleo: conecta os contratos, o grafo de dependências,
as fases canônicas e as capacidades já implementadas.

Regra: um módulo PENDING_INFRASTRUCTURE nunca é executado como se estivesse ativo.
Um módulo sem handler operacional explícito permanece observável, mas não é
considerado executado.
"""
from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.contracts.registry import ModuleRegistry
from sara.contracts.invariants import InvariantValidator


@dataclass(frozen=True)
class ConnectedAction:
    phase: str
    module: str
    status: str
    executed: bool
    ok: bool
    operation: str
    detail: dict[str, Any]
    blocking: bool = False


class ConnectedRuntime:
    """Executa a integração transversal sem duplicar o núcleo do ciclo."""

    NAME = "ConnectedRuntime"
    VERSION = "1.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.META
    DEPENDENCIES: tuple[str, ...] = ()
    CYCLE_PHASES = tuple(CyclePhase)

    # O RegenerativeLoop já executa estes módulos como núcleo de fase.
    CORE_HANDLED = {
        "DNA_Tags", "ARA", "ARA_Extended", "IdentityCore",
        "ETR", "ETR_Extended", "ITR", "ITR_Extended",
        "EthicalFilterChain", "RegenerativeMemory", "TemporalVectorDB",
        "EmergencyRollback", "DecisionTrace", "ProvenanceTracker",
        "RegenerativeLoop", "CycleAuditor",
    }

    def __init__(self, registry: ModuleRegistry, *, vagus_bus: Any | None = None) -> None:
        self._registry = registry
        self._vagus = vagus_bus
        self._validator = InvariantValidator()
        self._last_actions: list[ConnectedAction] = []

    def describe(self) -> dict:
        return {
            "name": self.NAME,
            "version": self.VERSION,
            "status": self.STATUS.value,
            "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "connected_modules": len(self._registry.snapshot()["modules"]),
            "vagus_bound": self._vagus is not None,
        }

    def validate_connection(self) -> dict:
        report = self._validator.validate_registry(self._registry)
        try:
            order = self._registry.dependency_order()
        except Exception as exc:
            invariant_payload = report.as_dict()
            invariant_payload["ok"] = False
            invariant_payload["blocking_failures"] = [
                *invariant_payload.get("blocking_failures", []),
                f"dependency_graph:{type(exc).__name__}:{exc}",
            ]
            return {
                "ok": False,
                "invariants": invariant_payload,
                "dependency_order": [],
                "connected_count": 0,
            }
        return {
            "ok": report.ok,
            "invariants": report.as_dict(),
            "dependency_order": order,
            "connected_count": len(order),
        }

    def dispatch_phase(self, ctx: Any, phase: CyclePhase) -> list[ConnectedAction]:
        """Conecta os módulos não-nucleares à fase atual.

        Não chama métodos desconhecidos. Para lógica real, usa somente APIs
        explicitamente existentes ou o hook process_phase implementado pelo módulo.
        """
        actions: list[ConnectedAction] = []
        for name in self._registry.dependency_order():
            if name in self.CORE_HANDLED or name == self.NAME:
                continue
            # SoulETROmegaSystem mantém fases internas próprias, mas sua
            # execução federada no SARA outer-cycle ocorre uma única vez,
            # na fase de monitoramento. As demais fases não recebem no-op.
            if name == "SoulETROmegaSystem" and phase != CyclePhase.MONITORING:
                continue
            entry = self._registry.get(name)
            if entry is None:
                continue
            if phase not in entry.phases:
                continue

            module = entry.instance
            if entry.status == ModuleStatus.PENDING_INFRASTRUCTURE:
                local_operation = getattr(module, "execute_local", None)
                if local_operation is not None:
                    try:
                        result = local_operation(ctx)
                        action = ConnectedAction(
                            phase.value, name, entry.status.value, True, True,
                            "local_operation",
                            result if isinstance(result, dict) else {"result": result},
                            blocking=True,
                        )
                    except Exception as exc:
                        action = ConnectedAction(
                            phase.value, name, entry.status.value, False, False,
                            "local_operation_error",
                            {"error": f"{type(exc).__name__}: {exc}"},
                            blocking=True,
                        )
                    actions.append(action)
                    self._record(ctx, action)
                    continue
                action = ConnectedAction(
                    phase.value, name, entry.status.value, False, True,
                    "pending_infrastructure",
                    {"reason": "infraestrutura externa ainda não configurada"},
                )
                actions.append(action)
                self._record(ctx, action)
                continue

            try:
                result = self._execute_known(module, name, phase, ctx)
                if result is None:
                    hook = getattr(module, "process_phase", None)
                    if hook is not None:
                        result = hook(phase, ctx)
                        operation = "process_phase"
                    else:
                        emitter = getattr(module, "emit_trace", None)
                        if emitter is not None:
                            emitter(ctx)
                            result = {"observability_only": True}
                            operation = "emit_trace"
                        else:
                            result = {"no_phase_operation": True}
                            operation = "none"
                else:
                    operation = result.pop("_operation", "module_api")

                action = ConnectedAction(
                    phase.value, name, entry.status.value, operation != "none",
                    True, operation, result if isinstance(result, dict) else {"result": result},
                )
            except Exception as exc:
                action = ConnectedAction(
                    phase.value, name, entry.status.value, False, False,
                    "error", {"error": f"{type(exc).__name__}: {exc}"},
                )
            if not action.ok and action.operation not in {"none", "emit_trace"}:
                action = ConnectedAction(
                    action.phase, action.module, action.status,
                    action.executed, action.ok, action.operation,
                    action.detail, blocking=True,
                )
            actions.append(action)
            self._record(ctx, action)

        self._last_actions.extend(actions)
        return actions

    def _execute_known(self, module: Any, name: str,
                       phase: CyclePhase, ctx: Any) -> dict[str, Any] | None:
        state = {
            "cycle_id": getattr(ctx, "cycle_id", ""),
            "current": getattr(ctx, "current", ""),
            "input": getattr(ctx, "input", ""),
            "phase": phase.value,
        }

        if phase == CyclePhase.PERSISTENCE and name == "ERU_Engine":
            h = module.freeze(
                f"cycle:{state['cycle_id']}:phase:{phase.value}",
                state,
            )
            return {"_operation": "eru_freeze", "hash": h}

        if phase == CyclePhase.SNAPSHOT and name == "QuantumSnapshotSystem":
            sid = module.snapshot(state)
            return {"_operation": "quantum_snapshot", "snapshot_id": sid}

        if phase == CyclePhase.MONITORING and name == "SoulETROmegaSystem":
            parent_cycle_id = state["cycle_id"]
            report = module.run_cycle(
                cycle_id=f"omega::{parent_cycle_id}",
                facts={
                    "parent_cycle_id": parent_cycle_id,
                    "current_input_length": len(state["current"]),
                },
            )
            return {
                "_operation": "omega_cycle",
                "cycle_id": report.cycle_id,
                "ok": report.ok,
                "health_score": report.evidence.get("health_score"),
                "metric_count": len(report.evidence.get("metrics", [])),
                "planned_actions": len(report.plan.actions),
            }

        if phase == CyclePhase.MONITORING and name == "GovernanceBackend":
            snap = module.snapshot()
            return {
                "_operation": "governance_snapshot",
                "decisions": snap.last_decisions,
                "modules": len(snap.modules),
            }

        if phase == CyclePhase.GOVERNANCE and name == "LegalAI":
            # A cadeia local de licenças é real; a consulta de patentes permanece externa.
            decision = module.validate_license(
                "SARA-cycle",
                "MIT",
            )
            return {
                "_operation": "legal_license_validation",
                "approved": decision.approved,
                "hash": decision.hash,
            }

        if phase == CyclePhase.GOVERNANCE and name == "ARAForge":
            manifest = {
                "name": "SARA-cycle",
                "core_functionality_prompt": state["current"],
            }
            adapted = module.adapt(
                manifest,
                ["preservar estado", "manter rastreabilidade", "não excluir componentes"],
            )
            return {
                "_operation": "ara_forge_adaptation",
                "name": adapted.name,
                "constraints": list(adapted.constraints),
            }

        if phase == CyclePhase.GOVERNANCE and name == "InnovationRadar":
            score = module.score({
                "name": "SARA-cycle",
                "description": state["current"],
                "license": "MIT",
                "dependencies": [],
            })
            return {
                "_operation": "innovation_score",
                "score": score.as_dict(),
            }

        if phase == CyclePhase.GOVERNANCE and name == "NeuralLens":
            text = state["current"]
            # Só analisa quando a entrada é sintaticamente Python.
            try:
                structure = module.extract(text, "python")
            except (SyntaxError, ValueError):
                return {
                    "_operation": "neural_lens_skipped",
                    "reason": "entrada não é código Python válido",
                }
            return {
                "_operation": "neural_lens_static",
                "functions": len(structure.functions),
                "classes": len(structure.classes),
                "imports": len(structure.imports),
                "lines": structure.lines,
            }

        if phase == CyclePhase.GOVERNANCE and name == "GovernedSARA":
            proposal = {
                "name": "SARA-cycle-state",
                "description": state["current"],
                "license": "MIT",
                "compliance_context": {"source": "connected_runtime"},
            }
            decision = module.assimilate(proposal, ctx=ctx)
            return {
                "_operation": "governed_assimilation",
                "accepted": decision.accepted,
                "reasons": list(decision.reasons),
            }

        return None

    def _record(self, ctx: Any, action: ConnectedAction) -> None:
        vagus_publish = "UNMEASURABLE"
        if self._vagus is not None:
            try:
                self._vagus.publish_sync(
                    "SARA.ConnectedRuntime",
                    action.module,
                    "module.action",
                    {
                        "cycle_id": getattr(ctx, "cycle_id", ""),
                        "phase": action.phase,
                        "module": action.module,
                        "operation": action.operation,
                        "executed": action.executed,
                        "ok": action.ok,
                    },
                    status="EXECUTE" if action.ok else "ERROR",
                    correlation_id=getattr(ctx, "cycle_id", None),
                    priority=80 if action.blocking else 40,
                    ttl=5_000,
                )
                vagus_publish = "VERIFIED"
            except Exception as exc:
                vagus_publish = f"BLOCKED:{type(exc).__name__}:{exc}"

        if hasattr(ctx, "record"):
            info = dict(action.detail)
            info.setdefault("operation", action.operation)
            info["vagus_publish"] = vagus_publish
            ctx.record(
                action.phase,
                action.module,
                action.ok,
                connected=True,
                executed=action.executed,
                **info,
            )

    def last_actions(self) -> list[ConnectedAction]:
        return list(self._last_actions)
