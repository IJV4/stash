from stash.config import ProviderSettings


def bearer_headers(settings: ProviderSettings) -> dict[str, str]:
    if not settings.api_key:
        return {}
    return {"Authorization": f"Bearer {settings.api_key}"}
