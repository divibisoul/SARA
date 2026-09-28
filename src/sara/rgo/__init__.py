"""RGO — Regra de Ouro integration boundary for SARA."""
from .engine import RGOEngine, RGOState
from .bugshield_adapter import from_bugshield
from .contracts import RGOEnvelope, RGOValidationError

__all__ = ["RGOEngine", "RGOState", "RGOEnvelope", "RGOValidationError", "from_bugshield"]
