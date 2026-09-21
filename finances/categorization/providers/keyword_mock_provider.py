import re
import unicodedata
from typing import Sequence

from ..contracts import (
    CategorizationCandidate,
    CategorizationProvider,
    CategorizationSuggestion,
    CategoryOption,
)


class KeywordMockCategorizationProvider(CategorizationProvider):
    """Shared deterministic behavior for mocked AI provider adapters."""

    provider_name = "mock"
    confidence = 0.90
    category_hints = {
        ("transport", "transporte"): (
            "uber",
            "taxi",
            "metro",
            "combustivel",
            "gasolina",
        ),
        ("food", "alimentacao"): (
            "ifood",
            "restaurant",
            "restaurante",
            "mercado",
            "supermercado",
        ),
        ("housing", "moradia"): (
            "rent",
            "aluguel",
            "energia",
            "electricity",
            "water",
            "agua",
        ),
        ("salary", "salario"): ("salary", "salario", "payroll", "folha"),
        ("health", "saude"): (
            "pharmacy",
            "farmacia",
            "doctor",
            "medico",
            "hospital",
        ),
    }

    def suggest_categories(
        self,
        *,
        candidates: Sequence[CategorizationCandidate],
        categories: Sequence[CategoryOption],
    ) -> Sequence[CategorizationSuggestion]:
        suggestions = []
        for candidate in candidates:
            match = self._match_category(candidate.description, categories)
            if not match:
                continue

            category, matched_hint = match
            suggestions.append(
                CategorizationSuggestion(
                    reference=candidate.reference,
                    category_id=category.id,
                    confidence=self.confidence,
                    reasoning=(
                        f"Mock {self.provider_name} matched '{matched_hint}' "
                        f"to '{category.name}'."
                    ),
                )
            )
        return suggestions

    def _match_category(self, description, categories):
        normalized_description = self._normalize(description)

        for category in categories:
            category_name = self._normalize(category.name)
            if category_name and category_name in normalized_description:
                return category, category_name

        for category in categories:
            category_name = self._normalize(category.name)
            for aliases, hints in self.category_hints.items():
                if not any(alias in category_name for alias in aliases):
                    continue
                matched_hint = next(
                    (hint for hint in hints if hint in normalized_description),
                    None,
                )
                if matched_hint:
                    return category, matched_hint

        return None

    @staticmethod
    def _normalize(value):
        normalized = unicodedata.normalize("NFKD", value or "")
        normalized = "".join(
            character
            for character in normalized
            if not unicodedata.combining(character)
        )
        normalized = re.sub(r"[^a-z0-9]+", " ", normalized.casefold())
        return " ".join(normalized.split())
