import logging
import subprocess
from collections.abc import Callable, Sequence

from stash.gpu.port import GpuSample

CommandRunner = Callable[[Sequence[str]], str]

NVIDIA_SMI_COMMAND = (
    "nvidia-smi",
    "--query-gpu=memory.total,memory.used,utilization.gpu",
    "--format=csv,noheader,nounits",
)
COMMAND_TIMEOUT_SECONDS = 10
FIELD_SEPARATOR = ","
MAX_LOGGED_REASON = 100

logger = logging.getLogger(__name__)


def run_command(args: Sequence[str], timeout_seconds: float = COMMAND_TIMEOUT_SECONDS) -> str:
    completed = subprocess.run(
        list(args),
        check=True,
        capture_output=True,
        text=True,
        timeout=timeout_seconds,
    )
    return completed.stdout


def parse_nvidia_smi(output: str) -> GpuSample:
    row = _first_row(output)
    try:
        total_mib, used_mib, utilization_pct = (int(field) for field in row.split(FIELD_SEPARATOR))
    except ValueError:
        raise ValueError(f"unreadable nvidia-smi row: {row!r}") from None
    return GpuSample(total_mib, used_mib, utilization_pct)


def _first_row(output: str) -> str:
    for line in output.splitlines():
        if line.strip():
            return line
    raise ValueError("nvidia-smi printed no GPU row")


class NvidiaSmiProbe:
    def __init__(self, run: CommandRunner) -> None:
        self._run = run

    def sample(self) -> GpuSample | None:
        try:
            output = self._run(NVIDIA_SMI_COMMAND)
            return parse_nvidia_smi(output)
        except OSError as error:
            logger.warning("nvidia-smi unavailable: %s", type(error).__name__)
        except subprocess.SubprocessError as error:
            logger.warning("nvidia-smi failed: %s", type(error).__name__)
        except ValueError as error:
            logger.warning("nvidia-smi output not understood: %s", str(error)[:MAX_LOGGED_REASON])
        return None
