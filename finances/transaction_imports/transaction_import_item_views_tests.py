from decimal import Decimal

from django.contrib.auth.models import User
from django.test import TestCase
from django.urls import reverse
from django.utils import timezone
from rest_framework import status
from rest_framework.test import APIClient

from finances.models import (
    Account,
    Category,
    Transaction,
    TransactionCategoryRule,
    TransactionImport,
    TransactionImportItem,
)


class TransactionImportItemViewSetTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass123")
        self.client = APIClient()
        self.client.force_authenticate(self.user)
        self.account = Account.objects.create(
            owner=self.user,
            name="Main Account",
            slug="main-account",
        )
        self.generic_category = Category.objects.create(
            owner=self.user,
            name="Debit",
            slug="debit",
        )
        self.transport = Category.objects.create(
            owner=self.user,
            name="Transport",
            slug="transport",
        )
        self.transaction_import = TransactionImport.objects.create(
            owner=self.user,
            source=TransactionImport.ImportSource.OFX,
            status=TransactionImport.ImportStatus.AWAITING_REVIEW,
        )
        self.item = TransactionImportItem.objects.create(
            owner=self.user,
            transaction_import=self.transaction_import,
            kind_of_transaction=Transaction.KindOfTransaction.EXPENSE,
            amount=Decimal("24.90"),
            date=timezone.now(),
            description="UBER *TRIP 8392",
            account=self.account,
            suggested_category=self.generic_category,
        )

    def test_approve_creates_transaction_and_learns_rule(self):
        response = self.client.post(
            reverse("transactionimportitem-approve", args=[self.item.id]),
            {"category": self.transport.id, "remember_choice": True},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.transaction_import.refresh_from_db()
        self.assertEqual(self.item.review_status, TransactionImportItem.ReviewStatus.APPROVED)
        self.assertEqual(self.item.categorization_source, TransactionImportItem.CategorizationSource.MANUAL)
        self.assertEqual(self.item.transaction.category, self.transport)
        self.assertEqual(
            self.transaction_import.status,
            TransactionImport.ImportStatus.COMPLETED,
        )
        rule = TransactionCategoryRule.objects.get(owner=self.user)
        self.assertEqual(rule.normalized_description, "uber trip")
        self.assertEqual(rule.category, self.transport)

    def test_approve_can_skip_learning(self):
        response = self.client.post(
            reverse("transactionimportitem-approve", args=[self.item.id]),
            {"category": self.transport.id, "remember_choice": False},
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.assertFalse(TransactionCategoryRule.objects.exists())

    def test_reject_does_not_create_transaction(self):
        response = self.client.post(
            reverse("transactionimportitem-reject", args=[self.item.id])
        )

        self.assertEqual(response.status_code, status.HTTP_200_OK)
        self.item.refresh_from_db()
        self.assertEqual(self.item.review_status, TransactionImportItem.ReviewStatus.REJECTED)
        self.assertFalse(Transaction.objects.exists())

    def test_cannot_approve_with_another_users_category(self):
        other_user = User.objects.create_user(username="other", password="pass123")
        foreign_category = Category.objects.create(
            owner=other_user,
            name="Foreign",
            slug="foreign",
        )

        response = self.client.post(
            reverse("transactionimportitem-approve", args=[self.item.id]),
            {"category": foreign_category.id, "remember_choice": True},
        )

        self.assertEqual(response.status_code, status.HTTP_400_BAD_REQUEST)
        self.assertFalse(Transaction.objects.exists())
