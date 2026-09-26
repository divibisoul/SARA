"""Federation adapters for SARA; native core remains authoritative."""
from .clareira_bridge import ClareiraBridge, clareira_bridge

__all__ = ["ClareiraBridge", "clareira_bridge"]
