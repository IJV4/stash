from stash.gpu.port import GpuSample


class FakeGpuProbe:
    def __init__(self, sample: GpuSample | None) -> None:
        self._sample = sample

    def sample(self) -> GpuSample | None:
        return self._sample


class FakeOwnVram:
    def __init__(self, mib: int = 0) -> None:
        self._mib = mib
        self.calls = 0

    def own_mib(self) -> int:
        self.calls += 1
        return self._mib
