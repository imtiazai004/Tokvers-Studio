"""Provider registry / factory — resolve a provider adapter by name."""
from .base import VideoProvider
from .grok import GrokProvider
from .higgsfield import HiggsfieldProvider
from .veo import VeoProvider

_PROVIDERS: dict[str, type[VideoProvider]] = {
    "veo": VeoProvider,
    "grok": GrokProvider,
    "higgsfield": HiggsfieldProvider,
}


def get_provider(name: str, **kwargs) -> VideoProvider:
    key = (name or "").lower()
    if key not in _PROVIDERS:
        raise ValueError(f"Unknown provider '{name}'. Available: {list(_PROVIDERS)}")
    return _PROVIDERS[key](**kwargs)


def available_providers() -> list[str]:
    return list(_PROVIDERS)
