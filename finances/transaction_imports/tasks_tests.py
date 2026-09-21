from decimal import Decimal
from unittest.mock import Mock, patch

from django.contrib.auth.models import User
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import TestCase
from django.utils import timezone

from finances.models import (
    Account,
    Category,
    Transaction,
    TransactionCategoryRule,
    TransactionImport,
    TransactionImportItem,
)

from finances.transaction_imports.tasks import process_transaction_import


class ProcessTransactionImportTaskTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(username="owner", password="pass123")
        self.account = Account.objects.create(
            owner=self.user,
            name="Checking",
            slug="checking",
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

    def make_import(self):
        return TransactionImport.objects.create(
            owner=self.user,
            source=TransactionImport.ImportSource.OFX,
            file=SimpleUploadedFile("statement.ofx", b"OFX test"),
        )

    def make_parsed_transaction(self):
        return Transaction(
            owner=self.user,
            kind_of_transaction=Transaction.KindOfTransaction.EXPENSE,
            amount=Decimal("24.90"),
            date=timezone.now(),
            description="UBER *TRIP 8392",
            category=self.generic_category,
            account=self.account,
        )

    @patch("finances.transaction_imports.orchestrator.ProcessorFactory.get_processor")
    def test_unknown_description_waits_for_human_review(self, get_processor):
        processor = Mock()
        processor.process.return_value = [self.make_parsed_transaction()]
        get_processor.return_value = processor
        transaction_import = self.make_import()

        process_transaction_import.run(transaction_import.id)

        transaction_import.refresh_from_db()
        item = TransactionImportItem.objects.get(transaction_import=transaction_import)
        self.assertEqual(
            transaction_import.status,
            TransactionImport.ImportStatus.AWAITING_REVIEW,
        )
        self.assertEqual(item.review_status, TransactionImportItem.ReviewStatus.PENDING_REVIEW)
        self.assertIsNone(item.transaction)
        self.assertFalse(Transaction.objects.exists())
        self.assertEqual(
            transaction_import.report_email_status,
            TransactionImport.ReportEmailStatus.NOT_SCHEDULED,
        )

    @patch("finances.transaction_imports.orchestrator.ProcessorFactory.get_processor")
    def test_learned_rule_skips_review_and_tracks_usage(self, get_processor):
        processor = Mock()
        processor.process.return_value = [self.make_parsed_transaction()]
        get_processor.return_value = processor
        rule = TransactionCategoryRule.objects.create(
            owner=self.user,
            normalized_description="uber trip",
            kind_of_transaction=Transaction.KindOfTransaction.EXPENSE,
            category=self.transport,
        )
        transaction_import = self.make_import()

        process_transaction_import.run(transaction_import.id)

        transaction_import.refresh_from_db()
        rule.refresh_from_db()
        item = TransactionImportItem.objects.get(transaction_import=transaction_import)
        self.assertEqual(transaction_import.status, TransactionImport.ImportStatus.COMPLETED)
        self.assertEqual(item.review_status, TransactionImportItem.ReviewStatus.APPROVED)
        self.assertEqual(item.categorization_source, TransactionImportItem.CategorizationSource.RULE)
        self.assertEqual(item.transaction.category, self.transport)
        self.assertEqual(rule.times_applied, 1)
        self.assertIsNotNone(rule.last_used_at)
        self.assertEqual(
            transaction_import.report_email_status,
            TransactionImport.ReportEmailStatus.SCHEDULED,
        )
