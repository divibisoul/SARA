"""SARA — Segurança: SafeSandbox.
Status: IMPLEMENTED (análise estática) | PENDING_INFRASTRUCTURE (execução isolada)
"""
from __future__ import annotations
import ast
from dataclasses import dataclass, field
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


FORBIDDEN_NAMES = {"os", "sys", "subprocess", "shutil", "socket",
                   "eval", "exec", "__import__"}


class IsolationBackend(Protocol):
    def execute(self, code: str, timeout_s: float, limits: dict | None) -> "SandboxResult": ...
    def terminate(self, execution_id: str) -> None: ...


@dataclass
class StaticAnalysis:
    parsed: bool
    nodes: int
    vulnerabilities: list[str] = field(default_factory=list)


@dataclass
class SandboxResult:
    execution_id: str
    output: str
    exit_code: int
    resource_usage: dict


class SafeSandbox:
    NAME = "SafeSandbox"
    VERSION = "2.0"
    STATUS = ModuleStatus.PENDING_INFRASTRUCTURE
    ROLE = CycleRole.SECURITY
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.EXECUTION,)

    def __init__(self, isolation_backend: IsolationBackend | None = None) -> None:
        self._isolation = isolation_backend

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "isolation_backend": type(self._isolation).__name__ if self._isolation else None,
            "analyze_static_available": True,
            "execute_available": self._isolation is not None,
        }

    def analyze_static(self, code: str) -> StaticAnalysis:
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return StaticAnalysis(False, 0, [f"syntax_error:{exc.msg}"])
        vulns: list[str] = []
        nodes = 0
        for node in ast.walk(tree):
            nodes += 1
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_NAMES:
                        vulns.append(f"import_proibido:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in FORBIDDEN_NAMES:
                    vulns.append(f"import_from_proibido:{node.module}")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in {"eval", "exec", "__import__"}:
                    vulns.append(f"chamada_perigosa:{node.func.id}")
        return StaticAnalysis(True, nodes, vulns)

    def is_isolation_ready(self) -> bool:
        return self._isolation is not None

    def execute(self, code: str, timeout_s: float = 5.0, limits: dict | None = None) -> SandboxResult:
        if self._isolation is None:
            raise NotImplementedError(
                "SafeSandbox.execute requer backend de isolamento real "
                "(Docker, Firecracker, nsjail, bubblewrap ou similar). "
                "Nenhum backend foi injetado em SafeSandbox(isolation_backend=...). "
                "Ativação: ver CANONICAL_ACTIVATION_PLAN.for_module('SafeSandbox')."
            )
        executor = getattr(self._isolation, "execute", None)
        if not callable(executor):
            raise NotImplementedError(
                f"SafeSandbox.execute: backend '{type(self._isolation).__name__}' "
                "não expõe execute(code, timeout_s, limits)."
            )
        result = executor(code, timeout_s, limits or {})
        if not isinstance(result, SandboxResult):
            raise TypeError(
                "SafeSandbox backend execute deve retornar SandboxResult"
            )
        return result

    def terminate(self, execution_id: str) -> None:
        if self._isolation is None:
            raise NotImplementedError(
                "SafeSandbox.terminate requer backend de isolamento ativo."
            )
        terminator = getattr(self._isolation, "terminate", None)
        if not callable(terminator):
            raise NotImplementedError(
                f"SafeSandbox.terminate: backend '{type(self._isolation).__name__}' "
                "não expõe terminate(execution_id)."
            )
        terminator(execution_id)

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("execution", self.NAME,
                       self._isolation is not None,
                       isolation_backend=type(self._isolation).__name__ if self._isolation else None)