"""SARA ↔ SOUL federation contract.

This module does not create a second transport or a second capability implementation.
It describes how SOUL nuclei may consume the already-existing SARA HTTP operations.
Ownership remains with SARA; nucleus affinity is guidance for composition only.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Final


SARA_FEDERATION_CONTRACT_VERSION: Final[str] = "1.0.0"

SARA_OPERATIONS: Final[dict[str, dict]] = {
    "sara.health": {
        "version": "1.0.0",
        "endpoint": "/health",
        "method": "GET",
        "phases": ["monitoring"],
        "purpose": "consultar prontidão e integridade operacional do SARA",
        "requires_auth": False,
    },
    "sara.cycle": {
        "version": "1.0.0",
        "endpoint": "/v1/cycle",
        "method": "POST",
        "phases": ["ingestion", "audit", "regeneration", "identity", "ethics",
                   "strategy", "execution", "validation", "persistence",
                   "snapshot", "monitoring", "governance"],
        "purpose": "executar o ciclo regenerativo completo",
        "requires_auth": True,
    },
    "sara.audit": {
        "version": "1.0.0",
        "endpoint": "/v1/audit",
        "method": "POST",
        "phases": ["audit", "ethics", "validation"],
        "purpose": "auditar entrada sem solicitar regeneração",
        "requires_auth": True,
    },
    "sara.regenerate": {
        "version": "1.0.0",
        "endpoint": "/v1/regenerate",
        "method": "POST",
        "phases": ["audit", "regeneration", "ethics", "validation"],
        "purpose": "regenerar preservando a entrada e retornar evidência",
        "requires_auth": True,
    },
    "sara.state": {
        "version": "1.0.0",
        "endpoint": "/v1/state",
        "method": "GET",
        "phases": [],
        "purpose": "consultar estado operacional do SARA",
        "requires_auth": True,
    },
    "sara.capabilities": {
        "version": "1.0.0",
        "endpoint": "/v1/capabilities",
        "method": "GET",
        "phases": ["persistence"],
        "purpose": "descobrir contratos e capacidades do SARA",
        "requires_auth": True,
    },
    "sara.trace": {
        "version": "1.0.0",
        "endpoint": "/v1/trace/{cycle_id}",
        "method": "GET",
        "phases": ["persistence", "monitoring"],
        "purpose": "recuperar evidência correlacionada de um ciclo",
        "requires_auth": True,
    },
    "sara.clareira.state": {
        "version": "1.1.0",
        "endpoint": "/v1/clareira/state",
        "method": "POST",
        "phases": ["audit", "validation", "persistence", "monitoring"],
        "purpose": "receber, validar e congelar estado real do runtime Clareira",
        "requires_auth": True,
    },
    "sara.clareira.audit": {
        "version": "1.0.0",
        "endpoint": "/v1/clareira/audit",
        "method": "GET",
        "phases": ["audit", "strategy", "validation", "persistence"],
        "purpose": "consultar a avaliação cruzada ERU→MMD→RGO→Tríade do último estado Clareira",
        "requires_auth": True,
    },
    "sara.clareira.vagus": {
        "version": "1.1.0",
        "endpoint": "/v1/clareira/vagus",
        "method": "POST",
        "phases": ["strategy", "execution", "monitoring"],
        "purpose": "enfileirar comando vagal para entrega ao SOUL, sem alegar execução até ACK",
        "requires_auth": True,
    },
    "sara.clareira.vagus.pending": {
        "version": "1.1.0",
        "endpoint": "/v1/clareira/vagus/pending",
        "method": "GET",
        "phases": ["execution", "monitoring"],
        "purpose": "entregar comandos vagais pendentes ao SOUL",
        "requires_auth": True,
    },
    "sara.clareira.vagus.ack": {
        "version": "1.1.0",
        "endpoint": "/v1/clareira/vagus/ack",
        "method": "POST",
        "phases": ["execution", "monitoring"],
        "purpose": "registrar confirmação ou falha de execução no SOUL",
        "requires_auth": True,
    },
}


@dataclass(frozen=True)
class NucleusAffinity:
    nucleus: str
    role: str
    preferred_operations: tuple[str, ...]
    complementary_sara_modules: tuple[str, ...]
    connection_mode: str
    rationale: str

    def as_dict(self) -> dict:
        return {
            "nucleus": self.nucleus,
            "role": self.role,
            "preferred_operations": list(self.preferred_operations),
            "complementary_sara_modules": list(self.complementary_sara_modules),
            "connection_mode": self.connection_mode,
            "rationale": self.rationale,
        }


SOUL_NUCLEUS_AFFINITIES: Final[tuple[NucleusAffinity, ...]] = (
    NucleusAffinity(
        "N01",
        "host-reference-gateway / Android",
        ("sara.capabilities", "sara.state", "sara.trace", "sara.cycle"),
        ("ConnectedRuntime", "DecisionTrace", "GovernanceBackend"),
        "gateway-mediated",
        "N01 expõe o ponto de entrada do SOUL; SARA adiciona auditoria, estado e rastreabilidade ao fluxo sem assumir capacidades Android.",
    ),
    NucleusAffinity(
        "N02",
        "conversation / interaction",
        ("sara.audit", "sara.cycle", "sara.regenerate", "sara.trace"),
        ("ARA_Extended", "ETR_Extended", "ITR_Extended"),
        "context-enrichment",
        "N02 pode usar SARA para transformar entrada conversacional em contexto regenerativo verificável; a geração cognitiva continua N02.",
    ),
    NucleusAffinity(
        "N03",
        "perception / voice / multimodal",
        ("sara.audit", "sara.regenerate", "sara.trace"),
        ("ARA_Extended", "ETR_Extended", "SafeSandbox"),
        "content-validation",
        "N03 mantém áudio, fala e multimodalidade; SARA complementa com auditoria/regeneração do conteúdo textual ou metadados produzidos.",
    ),
    NucleusAffinity(
        "N04",
        "tools / documents / artifacts",
        ("sara.audit", "sara.regenerate", "sara.cycle", "sara.trace"),
        ("ARA_Extended", "ETR_Extended", "LegalAI", "ProvenanceTracker"),
        "artifact-governance",
        "N04 pode passar contexto e resultados de ferramentas/documentos pelo ciclo SARA sem duplicar seus executores.",
    ),
    NucleusAffinity(
        "N05",
        "orchestration / dispatch / execution",
        ("sara.cycle", "sara.audit", "sara.regenerate", "sara.trace"),
        ("TrinityERUUnified", "ConnectedRuntime", "CycleAuditor"),
        "orchestration-support",
        "N05 pode usar SARA como camada de validação/regeneração dentro da coordenação; a propriedade do despacho continua N05.",
    ),
    NucleusAffinity(
        "N06",
        "cognition / synthesis / audit / governance",
        ("sara.audit", "sara.state", "sara.trace", "sara.regenerate", "sara.cycle"),
        ("ERU_Engine", "GovernedSARA", "DecisionTrace", "ProvenanceTracker"),
        "cognitive-governance",
        "N06 é complementar aos mecanismos de auditoria e governança do SARA; nenhuma função cognitiva N06 é absorvida pelo SARA.",
    ),
)


def federation_manifest() -> dict:
    """Retorna um manifesto determinístico e serializável da federação."""
    return {
        "system": "SOUL↔SARA",
        "contract_version": SARA_FEDERATION_CONTRACT_VERSION,
        "ownership": "SARA-owns-SARA-operations; SOUL-nuclei-consume-through-composition",
        "non_destructive": True,
        "operations": {
            name: dict(spec) for name, spec in SARA_OPERATIONS.items()
        },
        "nucleus_affinities": [item.as_dict() for item in SOUL_NUCLEUS_AFFINITIES],
        "proof_rule": {
            "declared": "manifest-only",
            "configured": "URL + credential available",
            "connected": "real request + valid correlated response",
            "failed": "explicit error; never synthetic success",
        },
    }


def affinity_for(nucleus: str) -> NucleusAffinity | None:
    target = str(nucleus).strip().upper()
    return next((item for item in SOUL_NUCLEUS_AFFINITIES if item.nucleus == target), None)
