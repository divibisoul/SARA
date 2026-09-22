from .provenance import Provenance, RuleProvenance, ProvenanceTracker
from .ara import ARA, Flaw, RegeneratedText
from .etr import ETR, ValidationResult, Evidence
from .itr import ITR, Strategy, ExecutionResult
from .sistema_vivo import SistemaVivo, CycleResult

# ADICIONAR — Extensões da Trindade v3.0
from .ara_extended import ARA_Extended, StructuralFlaw, RuleUpgrade
from .etr_extended import ETR_Extended, MultiFrameworkResult, FrameworkAssessment, DecisionExplanation
from .itr_extended import ITR_Extended, StrategicPlan, ComposedResult, PatternReport, RegistryOptimization
from .trinity_synergy import TrinitySynergy, TrinityReport, TrinityIteration

__all__ = [
    "Provenance", "RuleProvenance", "ProvenanceTracker",
    "ARA", "Flaw", "RegeneratedText",
    "ETR", "ValidationResult", "Evidence",
    "ITR", "Strategy", "ExecutionResult",
    "SistemaVivo", "CycleResult",
    # ADICIONAR
    "ARA_Extended", "StructuralFlaw", "RuleUpgrade",
    "ETR_Extended", "MultiFrameworkResult", "FrameworkAssessment", "DecisionExplanation",
    "ITR_Extended", "StrategicPlan", "ComposedResult", "PatternReport", "RegistryOptimization",
    "TrinitySynergy", "TrinityReport", "TrinityIteration",
]