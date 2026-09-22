"""SARA — Pesquisa: NeuralLens.
Status: IMPLEMENTED (análise local) | PENDING_INFRASTRUCTURE (repositórios remotos)
"""
from __future__ import annotations
import ast
import base64
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase


@dataclass
class CodeStructure:
    module: str
    functions: list[str]
    classes: list[str]
    imports: list[str]
    lines: int
    revision: str | None = None
    source_sha: str | None = None


class NeuralLens:
    NAME = "NeuralLens"
    VERSION = "2.1"
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
            "remote_provenance": "git_blob_sha",
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
        return bool(os.getenv("GITHUB_TOKEN", "").strip())

    def extract_from_repo(self, repo_url: str, path: str, ref: str | None = None) -> CodeStructure:
        parsed = urllib.parse.urlparse(str(repo_url).strip())
        if parsed.scheme not in {"http", "https"}:
            raise ValueError("repo_url deve ser http/https")
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) < 2:
            raise ValueError("repo_url deve apontar para owner/repo")
        if "github.com" not in parsed.netloc.lower():
            raise ValueError("NEURAL_LENS_UNSUPPORTED_HOST")
        owner, repo = parts[0], parts[1].removesuffix(".git")
        clean_path = "/".join(p for p in str(path).split("/") if p)
        if not clean_path:
            raise ValueError("path é obrigatório")
        query_ref = str(ref or "").strip()
        if not query_ref:
            query_ref = urllib.parse.parse_qs(parsed.query).get("ref", [""])[0].strip()
        api = f"https://api.github.com/repos/{owner}/{repo}/contents/{urllib.parse.quote(clean_path, safe='/')}"
        if query_ref:
            api += "?" + urllib.parse.urlencode({"ref": query_ref})
        request = urllib.request.Request(
            api,
            headers={
                "Accept": "application/vnd.github+json",
                "User-Agent": "SARA-NeuralLens/2.1",
            },
        )
        token = os.getenv("GITHUB_TOKEN", "").strip()
        if token:
            request.add_header("Authorization", f"Bearer {token}")
        try:
            with urllib.request.urlopen(request, timeout=20) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(f"GitHub contents HTTP {exc.code}: {detail}") from exc
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"GitHub contents transport/JSON error: {exc}") from exc

        if not isinstance(payload, dict):
            raise RuntimeError("GitHub contents invalid response")
        source_sha = str(payload.get("sha") or "").strip() or None
        encoded = payload.get("content")
        encoding = str(payload.get("encoding") or "").lower()
        source = ""
        if isinstance(encoded, str) and encoding == "base64":
            try:
                source = base64.b64decode(encoded, validate=False).decode("utf-8")
            except (ValueError, UnicodeDecodeError) as exc:
                raise RuntimeError(f"GitHub contents base64 decode error: {exc}") from exc
        elif isinstance(payload.get("download_url"), str) and payload["download_url"].strip():
            raw_request = urllib.request.Request(
                payload["download_url"],
                headers={"Accept": "application/octet-stream", "User-Agent": "SARA-NeuralLens/2.1"},
            )
            if token:
                raw_request.add_header("Authorization", f"Bearer {token}")
            try:
                with urllib.request.urlopen(raw_request, timeout=20) as response:
                    source = response.read().decode("utf-8")
            except (urllib.error.HTTPError, urllib.error.URLError, UnicodeDecodeError) as exc:
                raise RuntimeError(f"GitHub raw contents error: {exc}") from exc
        else:
            raise RuntimeError("GitHub contents did not provide decodable source")

        structure = self.extract(source, "python")
        return CodeStructure(
            module=f"{owner}/{repo}/{clean_path}",
            functions=structure.functions,
            classes=structure.classes,
            imports=structure.imports,
            lines=structure.lines,
            revision=query_ref or None,
            source_sha=source_sha,
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