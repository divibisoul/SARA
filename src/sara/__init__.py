"""SARA — Sistema de Arquitetura Regenerativa Autônoma.
Versão 3.1
"""
from sara.core import ARA, ETR, ITR, SistemaVivo
from sara.core.provenance import Provenance, RuleProvenance, ProvenanceTracker
from sara.memory import DNA_Tags, TemporalVectorDB, RegenerativeMemory
from sara.security import (
    IdentityCore, EmergencyRollback, EthicalFilterChain, SafeSandbox,
)
from sara.regeneration import RegenerativeLoop, SynergyEngine
from sara.monitoring import StormMonitor, DecisionTrace, GovernanceBackend
from sara.governance import (
    UbuntuEthics, BuenVivir, LegalAI, LegalCompliance, GovernedSARA,
)
from sara.meta import (
    ARAForge, AssimilationReviewCommittee,
    QuantumSnapshotSystem, ERU_Engine, TransystemSARA,
)
from sara.research import (
    QuantumCrawler, NeuralLens, InnovationRadar,
    NeuroIntegrator, QuantumScanner,
)
from sara.audit import CycleAuditor
from sara.bootstrap import build_default_system, SaraSystem

__version__ = "3.1.0"

__all__ = [
    "ARA", "ETR", "ITR", "SistemaVivo",
    "Provenance", "RuleProvenance", "ProvenanceTracker",
    "DNA_Tags", "TemporalVectorDB", "RegenerativeMemory",
    "IdentityCore", "EmergencyRollback", "EthicalFilterChain", "SafeSandbox",
    "RegenerativeLoop", "SynergyEngine",
    "StormMonitor", "DecisionTrace", "GovernanceBackend",
    "UbuntuEthics", "BuenVivir", "LegalAI", "LegalCompliance", "GovernedSARA",
    "ARAForge", "AssimilationReviewCommittee",
    "QuantumSnapshotSystem", "ERU_Engine", "TransystemSARA",
    "QuantumCrawler", "NeuralLens", "InnovationRadar",
    "NeuroIntegrator", "QuantumScanner",
    "CycleAuditor", "build_default_system", "SaraSystem",
]