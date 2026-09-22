from __future__ import annotations
from dataclasses import dataclass
from typing import Any

from sara.omega.scanner import SystemMetricsScanner


@dataclass(frozen=True)
class DeviceCapabilities:
    platform: str
    privileged_operations: bool
    source: str


class DeviceAdapter:
    """Contrato HAL agnóstico de fabricante.

    O adapter não promete privilégios Android. Capacidades externas precisam
    ser fornecidas por uma ponte real (por exemplo, Shizuku) no SOUL.
    """
    NAME = "DeviceAdapter"

    def capabilities(self) -> DeviceCapabilities:
        raise NotImplementedError

    def collect_metrics(self) -> dict[str, float]:
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
