import httpx
from builders import an_ollama_settings, an_openrouter_settings
from http_wire import DEEPLY_NESTED

OLLAMA = an_ollama_settings()
OPENROUTER = an_openrouter_settings()
MALFORMED_BODIES: dict[str, httpx.Response] = {
    "not-json": httpx.Response(200, text="<html>nope</html>"),
    "json-array": httpx.Response(200, json=[]),
    "no-models-key": httpx.Response(200, json={"other": 1}),
    "models-not-a-list": httpx.Response(200, json={"models": "none"}),
    "deeply-nested": httpx.Response(200, text=DEEPLY_NESTED),
}
