from fakes.gpu import FakeGpuProbe, FakeOwnVram
from fakes.store_factories import FreshStore

from stash.config import GpuConfig
from stash.gpu.gate import GpuGate
from stash.gpu.port import GpuSample

CONFIG = GpuConfig(min_free_vram_mib=4000, max_foreign_utilization_pct=50, manual_off_hours=4.0)
TOTAL = 10000
USED_WHEN_FREE_EQUALS_MINIMUM = TOTAL - CONFIG.min_free_vram_mib


def a_sample(used_mib: int = 1000, utilization_pct: int = 5) -> GpuSample:
    return GpuSample(TOTAL, used_mib, utilization_pct)


def a_gate(
    sample: GpuSample | None,
    own_mib: int = 0,
    store: FreshStore | None = None,
    config: GpuConfig = CONFIG,
) -> GpuGate:
    return GpuGate(
        FakeGpuProbe(sample),
        FakeOwnVram(own_mib),
        FreshStore() if store is None else store,
        config,
    )
