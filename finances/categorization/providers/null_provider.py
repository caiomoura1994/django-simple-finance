from typing import Sequence

from ..contracts import (
    CategorizationCandidate,
    CategorizationProvider,
    CategorizationSuggestion,
    CategoryOption,
)


class NullCategorizationProvider(CategorizationProvider):
    """Provider used when automatic categorization is disabled."""

    def suggest_categories(
        self,
        *,
        candidates: Sequence[CategorizationCandidate],
        categories: Sequence[CategoryOption],
    ) -> Sequence[CategorizationSuggestion]:
        return []
