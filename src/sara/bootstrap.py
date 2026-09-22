"""SARA — Bootstrap v5.
Builds the complete modular runtime, validates invariants, and fails closed.
"""
from __future__ import annotations
from dataclasses import dataclass, field
import logging

from sara.contracts import ModuleRegistry
from sara.contracts.activation import CANONICAL_ACTIVATION_PLAN
from sara.contracts.invariants import InvariantValidator
from sara.core.ara import ARA
from sara.core.ara_extended import ARA_Extended
from sara.core.etr import ETR
from sara.core.etr_extended import ETR_Extended
from sara.core.itr import ITR
from sara.core.itr_extended import ITR_Extended
from sara.core.trinity_synergy import TrinitySynergy
from sara.core.sistema_vivo import SistemaVivo
from sara.core.provenance import ProvenanceTracker
from sara.memory.dna_tags import DNA_Tags
from sara.memory.temporal_vector_db import TemporalVectorDB
from sara.memory.regenerative_memory import RegenerativeMemory
from sara.security.identity_core import IdentityCore
from sara.security.emergency_rollback import EmergencyRollback
from sara.security.ethical_filter_chain import EthicalFilterChain
from sara.security.safe_sandbox import SafeSandbox
from sara.regeneration.regenerative_loop import RegenerativeLoop
from sara.regeneration.synergy_engine import SynergyEngine
from sara.monitoring.storm_monitor import StormMonitor
from sara.monitoring.decision_trace import DecisionTrace
from sara.monitoring.governance import GovernanceBackend
from sara.governance.ubuntu_ethics import UbuntuEthics
from sara.governance.buen_vivir import BuenVivir
from sara.governance.legal_ai import LegalAI
from sara.governance.legal_compliance import LegalCompliance
from sara.governance.governed_sara import GovernedSARA
from sara.meta.ara_forge import ARAForge
from sara.meta.assimilation_committee import AssimilationReviewCommittee
from sara.meta.quantum_snapshot import QuantumSnapshotSystem
from sara.meta.eru_engine import ERU_Engine
from sara.meta.transystem_sara import TransystemSARA
from sara.research.innovation_radar import InnovationRadar
from sara.research.neuro_integrator import NeuroIntegrator
from sara.research.neural_lens import NeuralLens
from sara.research.quantum_crawler import QuantumCrawler
from sara.research.quantum_scanner import QuantumScanner
from sara.audit.cycle_auditor import CycleAuditor

logger = logging.getLogger("SARA_BOOTSTRAP")


@dataclass
class SaraSystem:
    registry: ModuleRegistry
    sistema_vivo: SistemaVivo
    components: dict
    registration_report: dict = field(default_factory=dict)
    invariant_report: dict = field(default_factory=dict)
    ready: bool = False


def build_default_system(*, fail_closed: bool = True) -> SaraSystem:
    registry = ModuleRegistry()
    report = {"registered": [], "failed": [], "pending": []}

    prov = ProvenanceTracker()
    dna = DNA_Tags()
    temporal = TemporalVectorDB()
    memory = RegenerativeMemory()
    rollback = EmergencyRollback()
    trace = DecisionTrace()

    ara = ARA(dna, temporal, prov)
    ara_extended = ARA_Extended(dna, temporal, prov)
    identity = IdentityCore(prov)
    ubuntu = UbuntuEthics()
    buen = BuenVivir()
    etr = ETR(identity, ubuntu, buen, prov)
    etr_extended = ETR_Extended(identity, ubuntu, buen, prov)
    safe_sandbox = SafeSandbox(isolation_backend=None)
    itr = ITR(prov, safe_sandbox=safe_sandbox)
    itr_extended = ITR_Extended(prov, safe_sandbox=safe_sandbox)

    filters = EthicalFilterChain()
    filters.register(ubuntu)
    filters.register(buen)

    legal_compliance = LegalCompliance()
    legal_ai = LegalAI(allowed_licenses={"MIT", "Apache-2.0", "BSD-3-Clause"})
    committee = AssimilationReviewCommittee(quorum=0.75)
    committee.register_member("etr", lambda p: etr.validate(str(p.get("description", ""))).approved)
    committee.register_member("identity", lambda p: identity.validate(str(p.get("description", ""))).approved)
    committee.register_member("itr", lambda p: True)

    radar = InnovationRadar(etr, itr, identity)
    governed = GovernedSARA(committee, legal_compliance, radar=radar)
    ara_forge = ARAForge()
    quantum_snapshot = QuantumSnapshotSystem()
    eru = ERU_Engine()

    neuro = NeuroIntegrator(rollback, memory, registry=registry)
    neural_lens = NeuralLens()
    synergy_engine = SynergyEngine()
    quantum_crawler = QuantumCrawler(backends=[])
    quantum_scanner = QuantumScanner()
    transystem = TransystemSARA()

    storm = StormMonitor(interval_s=0.1)
    governance_backend = GovernanceBackend(module_status={})
    auditor = CycleAuditor()

    loop = RegenerativeLoop(
        ara=ara_extended, etr=etr_extended, itr=itr_extended,
        identity=identity, memory=memory, temporal=temporal, dna=dna,
        filters=filters, rollback=rollback, decision_trace=trace,
        provenance=prov, registry=registry, governance_backend=governance_backend,
        cycle_auditor=auditor, max_cycles=3,
    )
    sistema = SistemaVivo(loop, storm, trace, registry=registry, provenance=prov)
    trinity = TrinitySynergy(ara_extended, etr_extended, itr_extended)

    candidates = [
        prov, dna, temporal, memory, rollback, trace,
        ara, ara_extended, identity, ubuntu, buen, etr, etr_extended,
        safe_sandbox, itr, itr_extended, filters,
        legal_compliance, legal_ai, committee, radar, governed,
        ara_forge, quantum_snapshot, eru, neuro, neural_lens,
        synergy_engine, quantum_crawler, quantum_scanner, transystem,
        storm, governance_backend, auditor, loop, trinity, sistema,
    ]

    for module in candidates:
        name = getattr(module, "NAME", type(module).__name__)
        try:
            registry.register(module)
            report["registered"].append(name)
            if getattr(module, "STATUS", None) is not None and module.STATUS.value == "PENDING_INFRASTRUCTURE":
                report["pending"].append(name)
        except Exception as exc:
            logger.error("[bootstrap] registro falhou: %s: %s", name, exc)
            report["failed"].append({"module": name, "reason": str(exc)})

    invariant_report = InvariantValidator().validate_registry(registry).as_dict()
    if fail_closed and (report["failed"] or not invariant_report["ok"]):
        raise RuntimeError({
            "message": "SARA bootstrap fail-closed: invariantes não satisfeitas",
            "registration_report": report,
            "invariant_report": invariant_report,
        })

    return SaraSystem(
        registry=registry,
        sistema_vivo=sistema,
        registration_report=report,
        invariant_report=invariant_report,
        ready=not bool(report["failed"]) and invariant_report["ok"],
        components={
            "ara": ara, "ara_extended": ara_extended,
            "etr": etr, "etr_extended": etr_extended,
            "itr": itr, "itr_extended": itr_extended,
            "trinity": trinity, "identity": identity,
            "memory": memory, "temporal": temporal, "dna": dna,
            "filters": filters, "rollback": rollback, "trace": trace,
            "loop": loop, "sistema_vivo": sistema, "governed": governed,
            "radar": radar, "eru": eru, "neuro": neuro,
            "synergy": synergy_engine, "ubuntu": ubuntu, "buen": buen,
            "legal": legal_compliance, "legal_ai": legal_ai,
            "committee": committee, "storm": storm, "governance": governance_backend,
            "ara_forge": ara_forge, "snapshot": quantum_snapshot,
            "neural_lens": neural_lens, "quantum_crawler": quantum_crawler,
            "quantum_scanner": quantum_scanner, "safe_sandbox": safe_sandbox,
            "transystem": transystem, "auditor": auditor, "provenance": prov,
            "decision_trace": trace, "activation_plan": CANONICAL_ACTIVATION_PLAN,
        },
    )
