"""SARA — Segurança: SafeSandbox.
Status: IMPLEMENTED (análise estática) | PENDING_INFRASTRUCTURE (execução isolada)
"""
from __future__ import annotations
import ast
from dataclasses import dataclass, field
from typing import Protocol
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


FORBIDDEN_NAMES = {"os", "sys", "subprocess", "shutil", "socket",
                   "eval", "exec", "__import__", "ctypes", "multiprocessing"}
FORBIDDEN_CALLS = {
    "eval", "exec", "__import__", "compile",
    "open", "input",
}
FORBIDDEN_ATTRIBUTES = {
    "system", "popen", "spawn", "fork", "remove", "unlink",
    "write_text", "write_bytes", "__subclasses__", "__globals__",
    "__getattribute__", "__getattr__", "__class__",
}

MAX_SOURCE_CHARS = 1_000_000
MAX_AST_NODES = 50_000


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
    VERSION = "2.1"
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
            "execution_requires_external_isolation": True,
            "static_limits": {"max_source_chars": MAX_SOURCE_CHARS, "max_ast_nodes": MAX_AST_NODES},
        }

    def analyze_static(self, code: str) -> StaticAnalysis:
        if not isinstance(code, str):
            raise TypeError("SAFE_SANDBOX_SOURCE_MUST_BE_TEXT")
        if len(code) > MAX_SOURCE_CHARS:
            return StaticAnalysis(False, 0, [f"source_too_large:{MAX_SOURCE_CHARS}"])
        try:
            tree = ast.parse(code)
        except SyntaxError as exc:
            return StaticAnalysis(False, 0, [f"syntax_error:{exc.msg}"])
        except (MemoryError, RecursionError) as exc:
            return StaticAnalysis(False, 0, [f"analysis_resource_limit:{type(exc).__name__}"])
        vulns: list[str] = []
        nodes = 0
        for node in ast.walk(tree):
            nodes += 1
            if nodes > MAX_AST_NODES:
                return StaticAnalysis(False, nodes, [f"ast_too_large:{MAX_AST_NODES}"])
            if isinstance(node, ast.Import):
                for alias in node.names:
                    if alias.name.split(".")[0] in FORBIDDEN_NAMES:
                        vulns.append(f"import_proibido:{alias.name}")
            elif isinstance(node, ast.ImportFrom):
                if node.module and node.module.split(".")[0] in FORBIDDEN_NAMES:
                    vulns.append(f"import_from_proibido:{node.module}")
            elif isinstance(node, ast.Call):
                if isinstance(node.func, ast.Name) and node.func.id in FORBIDDEN_CALLS:
                    vulns.append(f"chamada_perigosa:{node.func.id}")
                elif isinstance(node.func, ast.Attribute) and node.func.attr in FORBIDDEN_ATTRIBUTES:
                    vulns.append(f"atributo_perigoso:{node.func.attr}")
        return StaticAnalysis(True, nodes, vulns)

    def is_isolation_ready(self) -> bool:
        return self._isolation is not None

    def execute(self, code: str, timeout_s: float = 5.0, limits: dict | None = None) -> SandboxResult:
        if not isinstance(code, str):
            raise TypeError("SAFE_SANDBOX_SOURCE_MUST_BE_TEXT")
        if len(code) > MAX_SOURCE_CHARS:
            raise ValueError(f"SAFE_SANDBOX_SOURCE_TOO_LARGE:{MAX_SOURCE_CHARS}")
        if self._isolation is None:
            raise RuntimeError("SAFE_SANDBOX_NOT_CONFIGURED")
        executor = getattr(self._isolation, "execute", None)
        if not callable(executor):
            raise RuntimeError(
                f"SAFE_SANDBOX_BACKEND_INVALID:{type(self._isolation).__name__}"
            )
        result = executor(code, timeout_s, limits or {})
        if not isinstance(result, SandboxResult):
            raise TypeError(
                "SafeSandbox backend execute deve retornar SandboxResult"
            )
        return result

    def terminate(self, execution_id: str) -> None:
        if self._isolation is None:
            raise RuntimeError("SAFE_SANDBOX_NOT_CONFIGURED")
        terminator = getattr(self._isolation, "terminate", None)
        if not callable(terminator):
            raise RuntimeError(
                f"SAFE_SANDBOX_BACKEND_INVALID:{type(self._isolation).__name__}"
            )
        terminator(execution_id)

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("execution", self.NAME,
                       self._isolation is not None,
                       isolation_backend=type(self._isolation).__name__ if self._isolation else None,
                       static_analysis_available=True,
                       execution_available=self._isolation is not None)