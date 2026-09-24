from __future__ import annotations
from abc import ABC, abstractmethod
from dataclasses import dataclass
from typing import Any

from sara.omega.scanner import SystemMetricsScanner


@dataclass(frozen=True)
class DeviceCapabilities:
    platform: str
    privileged_operations: bool
    source: str


class DeviceAdapter(ABC):
    """Contrato HAL agnóstico de fabricante.

    O adapter não promete privilégios Android. Capacidades externas precisam
    ser fornecidas por uma ponte real (por exemplo, Shizuku) no SOUL.
    """
    NAME = "DeviceAdapter"

    @abstractmethod
    def capabilities(self) -> DeviceCapabilities:
        """Return capabilities actually provided by the concrete adapter."""
        raise NotImplementedError

    @abstractmethod
    def collect_metrics(self) -> dict[str, float]:
        """Return metrics actually observable by the concrete adapter."""
        raise NotImplementedError


class GenericHostAdapter(DeviceAdapter):
    NAME = "GenericHostAdapter"

    def __init__(self, scanner: SystemMetricsScanner | None = None) -> None:
        self.scanner = scanner or SystemMetricsScanner()

    def capabilities(self) -> DeviceCapabilities:
        import platform
        return DeviceCapabilities(
            platform=platform.system().lower(),
            privileged_operations=False,
            source="python_host_observation",
        )

    def collect_metrics(self) -> dict[str, float]:
        return {m.name: m.value for m in self.scanner.scan()}
