import re
import unicodedata
from dataclasses import dataclass
from typing import Optional, Sequence

from django.contrib.auth.models import User
from loguru import logger

from finances.models import Category, Transaction, TransactionCategoryRule

from .contracts import CategorizationCandidate, CategoryOption
from .providers import get_categorization_provider


def normalize_transaction_description(description: str) -> str:
    """Create a stable key while removing accents, numbers and punctuation."""

    normalized = unicodedata.normalize("NFKD", description or "")
    normalized = "".join(char for char in normalized if not unicodedata.combining(char))
    normalized = normalized.casefold()
    normalized = re.sub(r"\d+", " ", normalized)
    normalized = re.sub(r"[^a-z]+", " ", normalized)
    return " ".join(normalized.split())[:255]


@dataclass(frozen=True)
class CategorizationDecision:
    category: Category
    source: str
    confidence: Optional[float] = None
    reasoning: str = ""
    rule: Optional[TransactionCategoryRule] = None


class CategorizationService:
    def __init__(self, provider=None):
        self.provider = provider or get_categorization_provider()

    def categorize(
        self,
        transactions: Sequence[Transaction],
        owner: User,
    ) -> dict[int, CategorizationDecision]:
        """Use learned rules first, then ask the configured provider in one batch."""

        rule_decisions = self.apply_learned_rules(transactions, owner)
        ai_decisions = self.suggest_with_ai(
            transactions,
            owner,
            resolved_indices=set(rule_decisions),
        )
        return {**rule_decisions, **ai_decisions}

    def apply_learned_rules(
        self,
        transactions: Sequence[Transaction],
        owner: User,
    ) -> dict[int, CategorizationDecision]:
        """Resolve transactions that the user has categorized before."""

        decisions: dict[int, CategorizationDecision] = {}
        rules = {
            (rule.normalized_description, rule.kind_of_transaction): rule
            for rule in TransactionCategoryRule.objects.filter(owner=owner).select_related("category")
        }

        for index, transaction in enumerate(transactions):
            key = (
                normalize_transaction_description(transaction.description),
                transaction.kind_of_transaction,
            )
            rule = rules.get(key)
            if rule:
                decisions[index] = CategorizationDecision(
                    category=rule.category,
                    source="RULE",
                    confidence=1.0,
                    reasoning="Previously confirmed by the user.",
                    rule=rule,
                )

        return decisions

    def suggest_with_ai(
        self,
        transactions: Sequence[Transaction],
        owner: User,
        resolved_indices: Optional[set[int]] = None,
    ) -> dict[int, CategorizationDecision]:
        """Ask the configured provider only about unresolved transactions."""

        resolved_indices = resolved_indices or set()
        decisions: dict[int, CategorizationDecision] = {}
        unresolved = [
            CategorizationCandidate(
                reference=str(index),
                description=transaction.description,
                kind_of_transaction=transaction.kind_of_transaction,
                amount=transaction.amount,
            )
            for index, transaction in enumerate(transactions)
            if index not in resolved_indices
        ]

        if not unresolved:
            return decisions

        categories = list(Category.objects.filter(owner=owner).order_by("name"))
        category_options = [
            CategoryOption(
                id=category.id,
                name=category.name,
                description=category.description,
            )
            for category in categories
        ]

        try:
            suggestions = self.provider.suggest_categories(
                candidates=unresolved,
                categories=category_options,
            )
        except Exception as exc:
            logger.error(
                "Categorization provider failed for user {}: {}",
                owner.id,
                str(exc),
            )
            return decisions

        unresolved_references = {candidate.reference for candidate in unresolved}
        categories_by_id = {category.id: category for category in categories}

        for suggestion in suggestions:
            if suggestion.reference not in unresolved_references:
                logger.warning("Ignoring categorization suggestion with unknown reference")
                continue

            category = categories_by_id.get(suggestion.category_id)
            if not category or not 0.0 <= suggestion.confidence <= 1.0:
                logger.warning("Ignoring invalid categorization suggestion")
                continue

            index = int(suggestion.reference)
            if index in decisions:
                continue

            decisions[index] = CategorizationDecision(
                category=category,
                source="AI",
                confidence=suggestion.confidence,
                reasoning=suggestion.reasoning,
            )

        return decisions
