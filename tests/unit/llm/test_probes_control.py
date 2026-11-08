import httpx
import pytest
from http_wire import Wire
from probe_rig import OLLAMA

from stash.llm import LlmUnavailable
from stash.llm.probes import OllamaControl


@pytest.mark.parametrize("status", [404, 500])
def test_unloading_raises_unavailable_on_a_non_success_status(status: int) -> None:
    # Setup
    control = OllamaControl(OLLAMA, Wire(httpx.Response(status)).client())

    # Execute / Assert
    with pytest.raises(LlmUnavailable, match=f"HTTP {status}"):
        control.unload()
