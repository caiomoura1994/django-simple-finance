from django.conf import settings
from django.utils.module_loading import import_string

from ..contracts import CategorizationProvider
from .gemini_provider import MockGeminiCategorizationProvider
from .grok_provider import MockGrokCategorizationProvider
from .null_provider import NullCategorizationProvider
from .openai_provider import MockOpenAICategorizationProvider


PROVIDER_ALIASES = {
    "none": NullCategorizationProvider,
    "mock_gemini": MockGeminiCategorizationProvider,
    "mock_openai": MockOpenAICategorizationProvider,
    "mock_grok": MockGrokCategorizationProvider,
}


def get_categorization_provider() -> CategorizationProvider:
    provider_reference = settings.AI_CATEGORIZATION_PROVIDER
    provider_class = PROVIDER_ALIASES.get(provider_reference)
    if provider_class is None:
        provider_class = import_string(provider_reference)
    provider = provider_class()

    if not isinstance(provider, CategorizationProvider):
        raise TypeError(
            f"{provider_reference} must implement CategorizationProvider"
        )

    return provider
