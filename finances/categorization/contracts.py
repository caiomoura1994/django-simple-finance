from abc import ABC, abstractmethod
from dataclasses import dataclass
from decimal import Decimal
from typing import Sequence


@dataclass(frozen=True)
class CategorizationCandidate:
    """Provider-neutral transaction data sent for categorization."""

    reference: str
    description: str
    kind_of_transaction: str
    amount: Decimal


@dataclass(frozen=True)
class CategoryOption:
    """A category the provider is allowed to select."""

    id: int
    name: str
    description: str = ""


@dataclass(frozen=True)
class CategorizationSuggestion:
    """Structured response expected from every AI provider adapter."""

    reference: str
    category_id: int
    confidence: float
    reasoning: str = ""


class CategorizationProvider(ABC):
    """Contract implemented by Gemini, Grok, Anthropic or any other provider."""

    @abstractmethod
    def suggest_categories(
        self,
        *,
        candidates: Sequence[CategorizationCandidate],
        categories: Sequence[CategoryOption],
    ) -> Sequence[CategorizationSuggestion]:
        """Return structured suggestions without creating or changing records."""
        raise NotImplementedError
