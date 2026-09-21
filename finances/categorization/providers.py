from django.conf import settings
from django.utils.module_loading import import_string
from typing import Sequence

from .contracts import (
    CategorizationCandidate,
    CategorizationProvider,
    CategorizationSuggestion,
    CategoryOption,
)


class NullCategorizationProvider(CategorizationProvider):
    """Safe default used until a real provider adapter is configured."""

    def suggest_categories(
        self,
        *,
        candidates: Sequence[CategorizationCandidate],
        categories: Sequence[CategoryOption],
    ) -> Sequence[CategorizationSuggestion]:
        return []


def get_categorization_provider() -> CategorizationProvider:
    provider_path = settings.AI_CATEGORIZATION_PROVIDER
    provider_class = import_string(provider_path)
    provider = provider_class()

    if not isinstance(provider, CategorizationProvider):
        raise TypeError(
            f"{provider_path} must implement CategorizationProvider"
        )

    return provider
