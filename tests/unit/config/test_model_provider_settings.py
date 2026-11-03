import pytest
from builders import API_KEY, an_ollama_settings, an_openrouter_settings

from stash.config import ConfigError


def test_provider_settings_with_blank_base_url_raises_config_error() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=r"llm\.ollama\.base_url"):
        an_ollama_settings(base_url="  ")


def test_provider_settings_with_blank_model_raises_config_error() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=r"llm\.ollama\.model"):
        an_ollama_settings(model="")


REJECTED_BASE_URLS = {
    "ftp-scheme": ("ftp://host/v1", "must start with http:// or https://"),
    "file-scheme": ("file:///etc/passwd", "must start with http:// or https://"),
    "no-scheme": ("/v1", "must start with http:// or https://"),
    "host-as-scheme": ("localhost:11434/v1", "must start with http:// or https://"),
    "no-host": ("http:///v1", "must include a host"),
    "user-and-password": ("http://user:pass@host/v1", "must not contain credentials"),
    "user-only": ("http://token@host/v1", "must not contain credentials"),
    "query": ("http://host/v1?key=1", "must not contain a query string or fragment"),
    "fragment": ("http://host/v1#top", "must not contain a query string or fragment"),
    "bad-port": ("http://host:abc/v1", "is not a valid URL"),
    "unclosed-ipv6": ("http://[::1/v1", "is not a valid URL"),
    "newline-in-path": ("http://host\n/v1", "is not a valid URL"),
    "carriage-return": ("http://host\r/v1", "is not a valid URL"),
    "tab": ("http://host\t/v1", "is not a valid URL"),
    "space-in-host": ("http://ho st/v1", "is not a valid URL"),
    "space-in-path": ("http://host/v 1", "is not a valid URL"),
    "trailing-space": ("http://host/v1 ", "is not a valid URL"),
    "leading-space": (" http://host/v1", "is not a valid URL"),
    "nul-character": ("http://host\x00/v1", "is not a valid URL"),
    "delete-character": ("http://host\x7f/v1", "is not a valid URL"),
    "zero-width-space": ("http://host\u200b/v1", "is not a valid URL"),
    "unicode-line-separator": ("http://host\u2028/v1", "is not a valid URL"),
}
ACCEPTED_BASE_URLS = [
    "http://localhost:11434/v1",
    "http://localhost:11434/v1/",
    "http://gpu-box/v1",
    "http://[::1]:11434/v1",
    "HTTPS://gpu-box.example/v1",
]


@pytest.mark.parametrize(
    ("base_url", "reason"), REJECTED_BASE_URLS.values(), ids=REJECTED_BASE_URLS.keys()
)
def test_provider_settings_reject_an_unusable_base_url_naming_the_key(
    base_url: str, reason: str
) -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=rf"llm\.ollama\.base_url {reason}"):
        an_ollama_settings(base_url=base_url)


@pytest.mark.parametrize("base_url", ACCEPTED_BASE_URLS)
def test_provider_settings_accept_an_http_or_https_base_url(base_url: str) -> None:
    # Execute
    settings = an_ollama_settings(base_url=base_url)

    # Assert
    assert settings.base_url == base_url


@pytest.mark.parametrize("base_url", ["http://hunter2 host/v1", "http://host\n/hunter2"])
def test_a_base_url_rejected_for_whitespace_never_echoes_its_value(base_url: str) -> None:
    # Execute
    with pytest.raises(ConfigError) as caught:
        an_ollama_settings(base_url=base_url)

    # Assert
    assert "hunter2" not in str(caught.value)


@pytest.mark.parametrize("base_url", ["http://user:hunter2@host/v1", "http://hunter2@host/v1"])
def test_a_rejected_base_url_never_echoes_its_credentials(base_url: str) -> None:
    # Execute / Assert
    with pytest.raises(ConfigError) as raised:
        an_ollama_settings(base_url=base_url)

    assert "hunter2" not in str(raised.value)


def test_openrouter_settings_reject_a_plain_http_base_url() -> None:
    # Execute / Assert
    with pytest.raises(ConfigError, match=r"llm\.openrouter\.base_url must use https"):
        an_openrouter_settings(base_url="http://openrouter.ai/api/v1")


def test_openrouter_settings_accept_a_trailing_slash_on_an_https_base_url() -> None:
    # Execute
    settings = an_openrouter_settings(base_url="https://openrouter.ai/api/v1/")

    # Assert
    assert settings.base_url == "https://openrouter.ai/api/v1/"


@pytest.mark.parametrize("base_url", ["http://localhost:11434/v1", "http://localhost:11434/v1/"])
def test_endpoint_appends_the_path_to_the_base_url_with_a_single_slash(base_url: str) -> None:
    # Setup
    settings = an_ollama_settings(base_url=base_url)

    # Execute
    endpoint = settings.endpoint("chat/completions")

    # Assert
    assert endpoint == "http://localhost:11434/v1/chat/completions"


@pytest.mark.parametrize("base_url", ["http://localhost:11434/v1", "http://localhost:11434/v1/"])
def test_native_endpoint_hangs_the_path_off_the_root_url(base_url: str) -> None:
    # Setup
    settings = an_ollama_settings(base_url=base_url)

    # Execute
    endpoint = settings.native_endpoint("api/tags")

    # Assert
    assert endpoint == "http://localhost:11434/api/tags"


def test_config_error_is_a_value_error() -> None:
    # Assert
    assert issubclass(ConfigError, ValueError)


@pytest.mark.parametrize(
    ("base_url", "root_url"),
    [
        ("http://localhost:11434/v1", "http://localhost:11434"),
        ("http://localhost:11434/v1/", "http://localhost:11434"),
        ("http://localhost:11434", "http://localhost:11434"),
        ("https://openrouter.ai/api/v1", "https://openrouter.ai/api"),
    ],
)
def test_provider_settings_root_url_strips_trailing_slash_and_v1(
    base_url: str, root_url: str
) -> None:
    # Setup
    settings = an_ollama_settings(base_url=base_url)

    # Assert
    assert settings.root_url == root_url


def test_provider_settings_repr_never_shows_the_api_key() -> None:
    # Assert
    assert API_KEY not in repr(an_openrouter_settings())


def test_provider_settings_api_key_and_vision_model_default_to_none() -> None:
    # Setup
    settings = an_ollama_settings()

    # Assert
    assert (settings.api_key, settings.vision_model) == (None, None)
