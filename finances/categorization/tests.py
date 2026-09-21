from decimal import Decimal
from unittest.mock import Mock

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APIClient

from finances.models import Account, Category, Transaction, TransactionCategoryRule

from .contracts import CategorizationProvider, CategorizationSuggestion
from .service import CategorizationService, normalize_transaction_description


class FakeCategorizationProvider(CategorizationProvider):
    def __init__(self, suggestions=None):
        self.suggestions = suggestions or []
        self.calls = []

    def suggest_categories(self, *, candidates, categories):
        self.calls.append({"candidates": candidates, "categories": categories})
        return self.suggestions


class CategorizationServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass123")
        self.account = Account.objects.create(
            owner=self.user,
            name="Main Account",
            slug="main-account",
        )
        self.transport = Category.objects.create(
            owner=self.user,
            name="Transport",
            slug="transport",
        )
        self.other = Category.objects.create(
            owner=self.user,
            name="Other",
            slug="other",
        )

    def make_transaction(self, description="UBER *TRIP 8392"):
        return Transaction(
            owner=self.user,
            kind_of_transaction=Transaction.KindOfTransaction.EXPENSE,
            amount=Decimal("24.90"),
            description=description,
            category=self.other,
            account=self.account,
        )

    def test_normalize_description_removes_accents_numbers_and_punctuation(self):
        self.assertEqual(
            normalize_transaction_description("  UBER *Viagem 8392 / SÃO PAULO "),
            "uber viagem sao paulo",
        )

    def test_learned_rule_is_used_without_calling_provider(self):
        TransactionCategoryRule.objects.create(
            owner=self.user,
            normalized_description="uber trip",
            kind_of_transaction=Transaction.KindOfTransaction.EXPENSE,
            category=self.transport,
        )
        provider = Mock(spec=CategorizationProvider)

        decisions = CategorizationService(provider=provider).categorize(
            [self.make_transaction()],
            self.user,
        )

        self.assertEqual(decisions[0].category, self.transport)
        self.assertEqual(decisions[0].source, "RULE")
        provider.suggest_categories.assert_not_called()

    def test_provider_receives_neutral_contract_and_returns_suggestion(self):
        provider = FakeCategorizationProvider(
            suggestions=[
                CategorizationSuggestion(
                    reference="0",
                    category_id=self.transport.id,
                    confidence=0.91,
                    reasoning="Ride service",
                )
            ]
        )

        decisions = CategorizationService(provider=provider).categorize(
            [self.make_transaction()],
            self.user,
        )

        self.assertEqual(decisions[0].category, self.transport)
        self.assertEqual(decisions[0].source, "AI")
        self.assertEqual(decisions[0].confidence, 0.91)
        self.assertEqual(provider.calls[0]["candidates"][0].description, "UBER *TRIP 8392")

    def test_invalid_provider_category_is_ignored(self):
        other_user = User.objects.create_user(username="other", password="pass123")
        foreign_category = Category.objects.create(
            owner=other_user,
            name="Foreign",
            slug="foreign",
        )
        provider = FakeCategorizationProvider(
            suggestions=[
                CategorizationSuggestion(
                    reference="0",
                    category_id=foreign_category.id,
                    confidence=0.99,
                )
            ]
        )

        decisions = CategorizationService(provider=provider).categorize(
            [self.make_transaction()],
            self.user,
        )

        self.assertEqual(decisions, {})


class TransactionCategoryRuleViewSetTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass123")
        self.other_user = User.objects.create_user(username="other", password="pass123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.transport = Category.objects.create(
            owner=self.user,
            name="Transport",
            slug="transport",
        )
        self.food = Category.objects.create(
            owner=self.user,
            name="Food",
            slug="food",
        )
        self.rule = TransactionCategoryRule.objects.create(
            owner=self.user,
            normalized_description="uber trip",
            kind_of_transaction=Transaction.KindOfTransaction.EXPENSE,
            category=self.transport,
        )
        TransactionCategoryRule.objects.create(
            owner=self.other_user,
            normalized_description="private rule",
            kind_of_transaction=Transaction.KindOfTransaction.EXPENSE,
            category=Category.objects.create(
                owner=self.other_user,
                name="Private",
                slug="private",
            ),
        )

    def test_list_only_returns_current_users_rules(self):
        response = self.client.get(reverse("transactioncategoryrule-list"))

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertEqual(response.data["count"], 1)
        self.assertEqual(response.data["results"][0]["id"], self.rule.id)

    def test_update_changes_rule_category(self):
        response = self.client.patch(
            reverse("transactioncategoryrule-detail", args=[self.rule.id]),
            {"category": self.food.id},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.rule.refresh_from_db()
        self.assertEqual(self.rule.category, self.food)
