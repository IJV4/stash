from fakes.fake_providers import FakeProviders
from provider_rig import (
    OPENROUTER_ONLY,
)

from stash.app.providers import model_unloader, own_vram_usage


def test_without_ollama_no_vram_counts_as_stashs_own_and_nothing_is_asked() -> None:
    # Setup
    providers = FakeProviders()

    # Execute
    own = own_vram_usage(OPENROUTER_ONLY, providers.client()).own_mib()

    # Assert
    assert (own, providers.requests) == (0, [])


def test_without_ollama_there_is_no_model_to_unload_and_nothing_is_sent() -> None:
    # Setup
    providers = FakeProviders()

    # Execute
    model_unloader(OPENROUTER_ONLY, providers.client()).unload()

    # Assert
    assert providers.requests == []
