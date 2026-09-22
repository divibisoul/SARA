"""SARA — Pesquisa: QuantumScanner.
Status: PENDING_INFRASTRUCTURE
"""
from __future__ import annotations
from typing import Literal
import ast
import hashlib
import pathlib
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


class QuantumScanner:
    NAME = "QuantumScanner"
    VERSION = "1.0"
    STATUS = ModuleStatus.PENDING_INFRASTRUCTURE
    ROLE = CycleRole.RESEARCH
    DEPENDENCIES = ()
    CYCLE_PHASES = ()

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "target_access_ready": self.is_target_access_ready(),
        }

    def is_target_access_ready(self) -> bool:
        return False

    def scan_source_file(self, target: str) -> dict:
        path = pathlib.Path(target)
        if not path.is_file():
            raise FileNotFoundError(f"target não encontrado: {target}")
        source = path.read_text(encoding="utf-8")
        digest = hashlib.sha256(source.encode("utf-8")).hexdigest()
        suffix = path.suffix.lower()
        result = {
            "target": str(path),
            "sha256": digest,
            "bytes": len(source.encode("utf-8")),
            "lines": len(source.splitlines()),
            "language": suffix,
            "functions": [],
            "classes": [],
            "imports": [],
            "syntax_valid": True,
            "findings": [],
        }
        if suffix == ".py":
            try:
                tree = ast.parse(source, filename=str(path))
            except SyntaxError as exc:
                result["syntax_valid"] = False
                result["findings"].append({
                    "kind": "syntax_error",
                    "line": exc.lineno,
                    "message": exc.msg,
                })
                return result
            for node in ast.walk(tree):
                if isinstance(node, ast.FunctionDef):
                    result["functions"].append(node.name)
                elif isinstance(node, ast.ClassDef):
                    result["classes"].append(node.name)
                elif isinstance(node, ast.Import):
                    result["imports"].extend(alias.name for alias in node.names)
                elif isinstance(node, ast.ImportFrom) and node.module:
                    result["imports"].append(node.module)
            return result
        result["findings"].append({
            "kind": "language_not_parser_supported",
            "message": "scanner local exige parser específico para análise estrutural desta linguagem",
        })
        return result

    def scan(self, target: str,
             depth: Literal["shallow", "deep", "atomic"] = "shallow") -> dict:
        raise NotImplementedError(
            "QuantumScanner.scan requer acesso a binário/código-fonte do alvo e "
            "ferramentas de análise profunda (parsers, disassemblers). "
            "Ativação: ver CANONICAL_ACTIVATION_PLAN.for_module('QuantumScanner')."
        )

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, False,
                       reason="PENDING_INFRASTRUCTURE")