"""Canonical Nervo Vago facade.

The runtime owns exactly one bus implementation: VagusNerveBus.
VagusBus/VagusNerveBus remain the compatibility names used by historical modules.
This module introduces the canonical architectural name without allocating a
second bus or duplicating transport state.
"""

from sara.infra.vagus_bus import VagusNerveBus

# Canonical name: one object, one implementation, one runtime authority.
NervoVago = VagusNerveBus

# Legacy compatibility alias. Existing imports continue to resolve to the same
# class and therefore cannot silently create a second transport authority.
VagusBus = NervoVago

__all__ = ["NervoVago", "VagusBus"]
