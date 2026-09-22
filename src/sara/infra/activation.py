"""SARA — ativação de backends reais a partir da infraestrutura disponível.
Nenhum backend sintético é criado: cada factory só retorna uma capacidade quando
há uma dependência operacional detectável e utilizável.
"""
from __future__ import annotations

import os
import shutil
import subprocess
import json
from dataclasses import dataclass
from typing import Any

from sara.security.safe_sandbox import IsolationBackend, SandboxResult
from sara.research.quantum_crawler import CrawlBackend, HTTPJSONBackend
from sara.governance.legal_ai import HTTPPatentOracle, PatentOracle
from sara.meta.transystem_sara import HTTPSystemAdapter, SystemAdapter


@dataclass
class DockerIsolationBackend:
    """Executa Python em container Docker sem rede e com limites explícitos."""

    image: str
    executable: str = "python"

    def execute(self, code: str, timeout_s: float, limits: dict | None) -> SandboxResult:
        cfg = limits or {}
        cpu = max(0.1, min(float(cfg.get("cpus", 1.0)), 4.0))
        memory = max(32, min(int(cfg.get("memory_mb", 256)), 4096))
        pids = max(16, min(int(cfg.get("pids", 64)), 512))
        result = subprocess.run(
            [
                "docker", "run", "--rm",
                "--network", "none",
                "--read-only",
                "--tmpfs", "/tmp:rw,noexec,nosuid,size=16m",
                "--cap-drop", "ALL",
                "--security-opt", "no-new-privileges",
                "--pids-limit", str(pids),
                "--memory", f"{memory}m",
                "--cpus", str(cpu),
                self.image, self.executable, "-",
            ],
            input=code,
            text=True,
            capture_output=True,
            timeout=max(0.1, float(timeout_s)),
            check=False,
        )
        return SandboxResult(
            execution_id=f"docker:{result.args[0]}:{result.returncode}",
            output=(result.stdout or "") + (result.stderr or ""),
            exit_code=result.returncode,
            resource_usage={"backend": "docker", "image": self.image, "cpus": cpu, "memory_mb": memory, "pids": pids},
        )

    def terminate(self, execution_id: str) -> None:
        # docker run síncrono já termina por timeout no processo pai.
        return None


def docker_backend_from_environment() -> IsolationBackend | None:
    docker = shutil.which("docker")
    if not docker:
        return None
    image = os.getenv("SARA_SANDBOX_DOCKER_IMAGE", "python:3.12-alpine").strip()
    if not image:
        return None
    try:
        subprocess.run(
            [docker, "image", "inspect", image],
            check=True,
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            timeout=3,
        )
    except (OSError, subprocess.SubprocessError):
        return None
    return DockerIsolationBackend(image=image)


def network_crawler_backends_from_environment() -> list[CrawlBackend]:
    """Backends HTTP públicos/reais; tokens são opcionais e somente server-side."""
    backends: list[CrawlBackend] = []
    backends.append(
        HTTPJSONBackend(
            "https://api.github.com/search/repositories?q={query}",
            token_env="GITHUB_TOKEN",
            source="GitHub",
        )
    )
    backends.append(
        HTTPJSONBackend(
            "https://huggingface.co/api/models?search={query}",
            token_env="HF_TOKEN",
            source="HuggingFace",
        )
    )
    return backends


def patent_oracle_from_environment() -> PatentOracle | None:
    endpoint = os.getenv("SARA_PATENT_ORACLE_URL", "").strip()
    if not endpoint:
        return None
    try:
        return HTTPPatentOracle(endpoint)
    except ValueError:
        return None


def transystem_adapters_from_environment() -> dict[str, SystemAdapter]:
    raw = os.getenv("SARA_TRANSYSTEM_ENDPOINTS_JSON", "").strip()
    if not raw:
        return {}
    try:
        parsed = json.loads(raw)
    except ValueError:
        return {}
    if not isinstance(parsed, dict):
        return {}
    token = os.getenv("SARA_TRANSYSTEM_TOKEN", "").strip()
    adapters: dict[str, SystemAdapter] = {}
    for system, endpoint in parsed.items():
        if not isinstance(system, str) or not isinstance(endpoint, str):
            continue
        try:
            adapters[system] = HTTPSystemAdapter(endpoint, token=token)
        except ValueError:
            continue
    return adapters


def environment_activation_report() -> dict[str, Any]:
    docker = docker_backend_from_environment()
    crawlers = network_crawler_backends_from_environment()
    patent_oracle = patent_oracle_from_environment()
    transystem = transystem_adapters_from_environment()
    return {
        "safe_sandbox": {"ready": docker is not None, "backend": type(docker).__name__ if docker else None},
        "quantum_crawler": {"ready": bool(crawlers), "backends": [type(b).__name__ for b in crawlers]},
        "legal_ai": {"patent_oracle_ready": patent_oracle is not None, "oracle": type(patent_oracle).__name__ if patent_oracle else None},
        "transystem_sara": {"ready": bool(transystem), "systems": sorted(transystem)},
        "github_token_present": bool(os.getenv("GITHUB_TOKEN", "").strip()),
        "hf_token_present": bool(os.getenv("HF_TOKEN", "").strip()),
    }
