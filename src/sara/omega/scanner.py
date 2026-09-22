from __future__ import annotations
import math
import os
import shutil
import time
from pathlib import Path

from sara.omega.models import ETRMetric, utc_now


class SystemMetricsScanner:
    """Coleta somente métricas realmente observáveis no host atual.

    A ausência de uma fonte não é preenchida com random/placeholder.
    """

    NAME = "SystemMetricsScanner"

    def scan(self) -> tuple[ETRMetric, ...]:
        now = utc_now()
        metrics: list[ETRMetric] = []
        cpu = self._cpu_percent()
        if cpu is not None:
            metrics.append(ETRMetric("cpu_utilization", cpu, "%", "procstat", now))
        memory = self._memory_percent()
        if memory is not None:
            metrics.append(ETRMetric("memory_utilization", memory, "%", "procmeminfo", now))
        disk = self._disk_percent()
        if disk is not None:
            metrics.append(ETRMetric("disk_utilization", disk, "%", "statvfs", now))
        network = self._network_bytes()
        if network is not None:
            metrics.append(ETRMetric("network_bytes_total", float(network), "bytes", "procnetdev", now))
        load = self._load1()
        if load is not None:
            metrics.append(ETRMetric("load_1m", load, "load", "os.getloadavg", now))
        battery = self._battery_percent()
        if battery is not None:
            metrics.append(ETRMetric("battery_percent", battery, "%", "sysfs", now))
        return tuple(metrics)

    @staticmethod
    def _cpu_sample() -> tuple[int, int] | None:
        try:
            line = Path("/proc/stat").read_text().splitlines()[0]
            values = [int(x) for x in line.split()[1:]]
            idle = values[3] + (values[4] if len(values) > 4 else 0)
            total = sum(values)
            return idle, total
        except (OSError, ValueError, IndexError):
            return None

    def _cpu_percent(self) -> float | None:
        a = self._cpu_sample()
        if a is None:
            return None
        time.sleep(0.02)
        b = self._cpu_sample()
        if b is None:
            return None
        idle_delta = b[0] - a[0]
        total_delta = b[1] - a[1]
        if total_delta <= 0:
            return None
        return max(0.0, min(100.0, 100.0 * (1.0 - idle_delta / total_delta)))

    @staticmethod
    def _memory_percent() -> float | None:
        try:
            values = {}
            for line in Path("/proc/meminfo").read_text().splitlines():
                k, v = line.split(":", 1)
                values[k] = float(v.strip().split()[0])
            total = values.get("MemTotal")
            available = values.get("MemAvailable")
            if not total or available is None:
                return None
            return max(0.0, min(100.0, 100.0 * (1.0 - available / total)))
        except (OSError, ValueError):
            return None

    @staticmethod
    def _disk_percent() -> float | None:
        try:
            total, used, _ = shutil.disk_usage(os.getcwd())
            return 100.0 * used / total if total else None
        except OSError:
            return None

    @staticmethod
    def _network_bytes() -> int | None:
        try:
            total = 0
            for line in Path("/proc/net/dev").read_text().splitlines()[2:]:
                _, data = line.split(":", 1)
                fields = data.split()
                if len(fields) >= 9:
                    total += int(fields[0]) + int(fields[8])
            return total
        except (OSError, ValueError):
            return None

    @staticmethod
    def _load1() -> float | None:
        try:
            return float(os.getloadavg()[0])
        except (AttributeError, OSError):
            return None

    @staticmethod
    def _battery_percent() -> float | None:
        roots = list(Path("/sys/class/power_supply").glob("BAT*/capacity"))
        for root in roots:
            try:
                return max(0.0, min(100.0, float(root.read_text().strip())))
            except (OSError, ValueError):
                continue
        return None
