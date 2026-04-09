"""
Konteyner / süreç kaynak metrikleri — Prometheus scrape (/metrics) ile Grafana'da tek yerden izleme.

- process_* metrikleri: prometheus_client ProcessCollector (Django export ile birlikte gelir).
- marifetli_container_*: cgroup v2/v1 bellek; Railway Linux konteynerlerinde genelde mevcuttur.
"""

from __future__ import annotations

import os

from prometheus_client.core import GaugeMetricFamily
from prometheus_client.registry import REGISTRY

_registered = False


class _CgroupMemoryCollector:
    """cgroup bellek (konteyner görünümü); yoksa hiç metrik üretmez."""

    def collect(self):
        # cgroup v2 (unified)
        cur_v2 = "/sys/fs/cgroup/memory.current"
        max_v2 = "/sys/fs/cgroup/memory.max"
        if os.path.isfile(cur_v2):
            try:
                with open(cur_v2, encoding="utf-8") as f:
                    current = int(f.read().strip())
                g = GaugeMetricFamily(
                    "marifetli_container_memory_usage_bytes",
                    "Konteyner cgroup bellek kullanımı (memory.current).",
                )
                g.add_metric([], float(current))
                yield g
            except (OSError, ValueError):
                pass
            try:
                with open(max_v2, encoding="utf-8") as f:
                    raw = f.read().strip()
                if raw and raw != "max":
                    limit = int(raw)
                    g = GaugeMetricFamily(
                        "marifetli_container_memory_limit_bytes",
                        "Konteyner bellek üst sınırı (memory.max); yoksa yayınlanmaz.",
                    )
                    g.add_metric([], float(limit))
                    yield g
            except (OSError, ValueError):
                pass
            return

        # cgroup v1
        cur_v1 = "/sys/fs/cgroup/memory/memory.usage_in_bytes"
        max_v1 = "/sys/fs/cgroup/memory/memory.limit_in_bytes"
        if os.path.isfile(cur_v1):
            try:
                with open(cur_v1, encoding="utf-8") as f:
                    current = int(f.read().strip())
                g = GaugeMetricFamily(
                    "marifetli_container_memory_usage_bytes",
                    "Konteyner cgroup bellek kullanımı (v1 memory.usage_in_bytes).",
                )
                g.add_metric([], float(current))
                yield g
            except (OSError, ValueError):
                pass
            try:
                with open(max_v1, encoding="utf-8") as f:
                    limit = int(f.read().strip())
                if limit > 0 and limit < (1 << 60):
                    g = GaugeMetricFamily(
                        "marifetli_container_memory_limit_bytes",
                        "Konteyner bellek üst sınırı (v1 memory.limit_in_bytes).",
                    )
                    g.add_metric([], float(limit))
                    yield g
            except (OSError, ValueError):
                pass


def register_prometheus_host_collectors() -> None:
    """Bir kez çağrılır; test/tekrar import güvenli."""
    global _registered
    if _registered:
        return
    _registered = True
    import prometheus_client.process_collector  # noqa: F401 — ProcessCollector kaydı

    REGISTRY.register(_CgroupMemoryCollector())
