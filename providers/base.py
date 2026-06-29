"""Provider-neutral interface + result type for video generation."""
from abc import ABC, abstractmethod
from dataclasses import dataclass, field


def raise_http(resp) -> None:
    """Like resp.raise_for_status(), but includes the response body so provider
    errors (e.g. why a 400 happened) are visible instead of a bare status code."""
    if resp.is_error:
        body = (resp.text or "")[:800]
        raise RuntimeError(
            f"HTTP {resp.status_code} from {resp.request.method} {resp.request.url} :: {body}"
        )


@dataclass
class GenerationResult:
    """Outcome of generating one video clip/scene."""
    output_path: str
    provider: str
    model: str
    duration_seconds: int
    latency_seconds: float
    cost_usd: float | None  # None when pricing is not configured (honest "unknown")
    raw: dict = field(default_factory=dict)


class VideoProvider(ABC):
    """
    A single video-generation backend.

    Adapters implement `generate()` for ONE clip/scene. Higher layers (pipeline,
    router) compose scenes and handle retries/fallback across providers.
    """

    name: str = "base"

    @abstractmethod
    async def generate(
        self,
        prompt: str,
        output_path: str,
        *,
        duration_seconds: int = 8,
        aspect_ratio: str = "9:16",
        resolution: str = "720p",
        reference_image_b64: str | None = None,
    ) -> GenerationResult:
        """
        Generate one clip from `prompt` and write it to `output_path`.

        `reference_image_b64` is an optional base64-encoded image (no data-URI
        prefix) used for character/product consistency (image-to-video). Each
        adapter formats it for its own API.
        """
        raise NotImplementedError
