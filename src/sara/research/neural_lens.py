"""SARA — Pesquisa: NeuralLens.
Status: IMPLEMENTED (análise local) | PENDING_INFRASTRUCTURE (repositórios remotos)
"""
from __future__ import annotations
import ast
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


@dataclass
class CodeStructure:
    module: str
    functions: list[str]
    classes: list[str]
    imports: list[str]
    lines: int


class NeuralLens:
    NAME = "NeuralLens"
    VERSION = "2.0"
    STATUS = ModuleStatus.IMPLEMENTED
    ROLE = CycleRole.RESEARCH
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "repo_client_ready": self.is_repo_client_ready(),
        }

    def extract(self, source_code: str, language: str = "python") -> CodeStructure:
        if language != "python":
            raise ValueError(f"NeuralLens.extract não suporta '{language}' ainda")
        tree = ast.parse(source_code)
        functions, classes, imports = [], [], []
        for node in ast.walk(tree):
            if isinstance(node, ast.FunctionDef):
                functions.append(node.name)
            elif isinstance(node, ast.ClassDef):
                classes.append(node.name)
            elif isinstance(node, ast.Import):
                imports.extend(a.name for a in node.names)
            elif isinstance(node, ast.ImportFrom):
                if node.module:
                    imports.append(node.module)
        return CodeStructure("", functions, classes, imports,
                             len(source_code.splitlines()))

    def is_repo_client_ready(self) -> bool:
        return False

    def extract_from_repo(self, repo_url: str, path: str) -> CodeStructure:
        raise NotImplementedError(
            "NeuralLens.extract_from_repo requer acesso a repositórios remotos "
            "(GitHub, GitLab) com token. "
            "Ativação: ver CANONICAL_ACTIVATION_PLAN.for_module('NeuralLens')."
        )

    def compare(self, a: CodeStructure, b: CodeStructure) -> dict:
        return {
            "functions_added": list(set(b.functions) - set(a.functions)),
            "functions_removed": list(set(a.functions) - set(b.functions)),
            "classes_added": list(set(b.classes) - set(a.classes)),
            "classes_removed": list(set(a.classes) - set(b.classes)),
            "imports_added": list(set(b.imports) - set(a.imports)),
            "imports_removed": list(set(a.imports) - set(b.imports)),
        }

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True,
                       repo_client_ready=self.is_repo_client_ready())