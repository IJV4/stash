from builders import BASE
from config_builders import an_llm_config, both_providers
from fakes.busy import FakeBusy

from stash.app.build import retry_gate
from stash.config import LlmTask, ProviderName


def test_the_auto_retry_waits_for_the_gpu_when_filing_runs_on_ollama() -> None:
    # Setup
    gate = FakeBusy(busy=True)

    # Execute
    busy = retry_gate(an_llm_config(), gate)(BASE)

    # Assert
    assert busy is True


def test_the_auto_retry_ignores_the_gpu_when_filing_runs_on_openrouter() -> None:
    # Setup
    llm = an_llm_config(providers=both_providers(), tasks={LlmTask.FILING: ProviderName.OPENROUTER})

    # Execute
    busy = retry_gate(llm, FakeBusy(busy=True))(BASE)

    # Assert
    assert busy is False


def test_the_auto_retry_ignores_the_gpu_when_a_busy_gpu_falls_back_to_openrouter() -> None:
    # Setup
    llm = an_llm_config(providers=both_providers(), busy_fallback="openrouter")

    # Execute
    busy = retry_gate(llm, FakeBusy(busy=True))(BASE)

    # Assert
    assert busy is False
