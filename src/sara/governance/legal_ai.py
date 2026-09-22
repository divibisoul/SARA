"""SARA — Governança: LegalAI.
Status: IMPLEMENTED (cadeia local) | PENDING_INFRASTRUCTURE (blockchain, patentes)
"""
from __future__ import annotations
from dataclasses import dataclass
import json
import os
import urllib.error
import urllib.parse
import urllib.request
from sara.contracts.base import ModuleStatus, CycleRole, CyclePhase
from sara.infra.hashing import chain_hash
from sara.infra.clock import now_iso


@dataclass
class LegalDecision:
    tech: str
    license: str
    approved: bool
    ts: str
    prev_hash: str
    hash: str


class PatentOracle:
    def check(self, tech_name: str, jurisdiction: str) -> dict: ...


class HTTPPatentOracle:
    def __init__(self, endpoint: str, timeout_s: float = 20.0) -> None:
        endpoint = endpoint.strip()
        if not endpoint.startswith(("http://", "https://")):
            raise ValueError("patent oracle endpoint deve ser http/https")
        self.endpoint = endpoint.rstrip("/")
        self.timeout_s = timeout_s

    def check(self, tech_name: str, jurisdiction: str) -> dict:
        params = urllib.parse.urlencode({"q": tech_name, "jurisdiction": jurisdiction})
        request = urllib.request.Request(
            f"{self.endpoint}?{params}",
            headers={"Accept": "application/json", "User-Agent": "SARA-LegalAI/2.1"},
        )
        try:
            with urllib.request.urlopen(request, timeout=self.timeout_s) as response:
                payload = json.loads(response.read().decode("utf-8"))
        except urllib.error.HTTPError as exc:
            detail = exc.read().decode("utf-8", "replace")[:500]
            raise RuntimeError(f"PATENT_ORACLE_HTTP_{exc.code}:{detail}") from exc
        except (urllib.error.URLError, json.JSONDecodeError) as exc:
            raise RuntimeError(f"PATENT_ORACLE_TRANSPORT_ERROR:{exc}") from exc
        if not isinstance(payload, dict):
            raise RuntimeError("PATENT_ORACLE_INVALID_RESPONSE")
        return payload


class LegalAI:
    NAME = "LegalAI"
    VERSION = "2.0"
    STATUS = ModuleStatus.PENDING_INFRASTRUCTURE
    ROLE = CycleRole.GOVERNANCE
    DEPENDENCIES = ()
    CYCLE_PHASES = (CyclePhase.GOVERNANCE,)

    def __init__(self, allowed_licenses: set[str], patent_oracle: PatentOracle | None = None) -> None:
        self._allowed = set(allowed_licenses)
        self._chain: list[LegalDecision] = []
        self._patent_oracle = patent_oracle

    def describe(self) -> dict:
        return {
            "name": self.NAME, "version": self.VERSION,
            "status": self.STATUS.value, "role": self.ROLE.value,
            "dependencies": list(self.DEPENDENCIES),
            "phases": [p.value for p in self.CYCLE_PHASES],
            "chain_length": len(self._chain),
            "patent_oracle_ready": self.is_patent_oracle_ready(),
        }

    def is_patent_oracle_ready(self) -> bool:
        return self._patent_oracle is not None

    def validate_license(self, tech_name: str, license_id: str) -> LegalDecision:
        prev = self._chain[-1].hash if self._chain else "GENESIS"
        approved = license_id in self._allowed
        payload = {"tech": tech_name, "license": license_id, "approved": approved}
        h = chain_hash(prev, payload)
        d = LegalDecision(tech_name, license_id, approved, now_iso(), prev, h)
        self._chain.append(d)
        return d

    def execute_local(self, ctx=None) -> dict:
        """Executa a parte local disponível sem fingir consulta de patentes."""
        decision = self.validate_license("SARA-cycle", "MIT")
        result = {
            "operation": "local_license_validation",
            "approved": decision.approved,
            "hash": decision.hash,
            "patent_oracle_ready": self.is_patent_oracle_ready(),
        }
        if ctx is not None and hasattr(ctx, "record"):
            ctx.record(
                "governance",
                self.NAME,
                decision.approved,
                **result,
            )
        return result

    def check_patent(self, tech_name: str, jurisdiction: str) -> dict:
        if not self._patent_oracle:
            return {
                "verified": False,
                "status": "BLOCKED_INFRASTRUCTURE",
                "reason": "patent_oracle_not_configured",
                "tech": tech_name,
                "jurisdiction": jurisdiction,
            }
        result = self._patent_oracle.check(tech_name, jurisdiction)
        if not isinstance(result, dict):
            raise RuntimeError("PATENT_ORACLE_INVALID_RESPONSE")
        # Transporte HTTP bem-sucedido não equivale a verificação jurídica.
        # O oracle precisa declarar explicitamente o resultado de verificação.
        verified = result.get("verified")
        if not isinstance(verified, bool):
            return {
                "verified": False,
                "status": "UNVERIFIED_ORACLE_RESPONSE",
                "tech": tech_name,
                "jurisdiction": jurisdiction,
                "oracle": type(self._patent_oracle).__name__,
                "verification_mode": "oracle_must_explicitly_verify",
                "result": result,
            }
        return {
            "verified": verified,
            "status": "VERIFIED" if verified else "NOT_VERIFIED",
            "tech": tech_name,
            "jurisdiction": jurisdiction,
            "oracle": type(self._patent_oracle).__name__,
            "verification_mode": "oracle_explicit_boolean",
            "result": result,
        }

    def verify_chain(self) -> bool:
        prev = "GENESIS"
        for d in self._chain:
            expected = chain_hash(prev, {"tech": d.tech, "license": d.license, "approved": d.approved})
            if expected != d.hash:
                return False
            prev = d.hash
        return True

    def chain(self) -> list[LegalDecision]:
        return list(self._chain)

    def emit_trace(self, ctx) -> None:
        if hasattr(ctx, "record"):
            ctx.record("governance", self.NAME, True,
                       chain_length=len(self._chain),
                       chain_valid=self.verify_chain())