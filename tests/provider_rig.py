from builders import an_ollama_settings, an_openrouter_settings
from config_builders import an_llm_config
from fakes.fake_providers import FakeProviders, thinking_fields

from stash.config import LlmTask, ProviderName, Thinking
from stash.llm import ChatMessage, ChatModel

OLLAMA = ProviderName.OLLAMA
OPENROUTER = ProviderName.OPENROUTER
SCHEMA = {"type": "object"}
BOTH = an_llm_config(
    providers={
        OLLAMA: an_ollama_settings(vision_model="llava"),
        OPENROUTER: an_openrouter_settings(),
    }
)
FILING_OFF = an_llm_config(providers=BOTH.providers, thinking={LlmTask.FILING: Thinking.OFF})
OPENROUTER_ONLY = an_llm_config(
    provider=OPENROUTER, providers={OPENROUTER: an_openrouter_settings()}
)


def first_request_json(providers: FakeProviders) -> dict[str, object]:
    return providers.chat_bodies(providers.requests[0].url.path)[0]


def thinking_fields_of(providers: FakeProviders) -> dict[str, object]:
    return thinking_fields(first_request_json(providers))


def ask(model: ChatModel) -> None:
    model.complete_json([ChatMessage.text("user", "hello")], SCHEMA, "probe")
