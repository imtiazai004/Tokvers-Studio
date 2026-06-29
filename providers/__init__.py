"""
Video provider abstraction layer.

A single, provider-neutral interface (`VideoProvider`) with concrete adapters for
each generation backend (Veo 3, Grok Imagine, …). The rest of the app talks to the
interface only — swapping or adding a provider is one adapter, no pipeline change.

This package is also what the Viability Probe runs against, so the moment a real
API key is available the core (does video generation actually work, at what
cost/quality) can be validated end-to-end with `python -m providers.probe`.
"""
from .base import VideoProvider, GenerationResult
from .registry import get_provider, available_providers

__all__ = ["VideoProvider", "GenerationResult", "get_provider", "available_providers"]
