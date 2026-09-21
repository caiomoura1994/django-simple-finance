from decimal import Decimal
from unittest.mock import patch

from django.contrib.auth.models import User
from django.core import mail
from django.test import TestCase, override_settings
from django.utils import timezone

from finances.models import Account, Category, Transaction, TransactionImport, TransactionImportItem

from finances.transaction_imports.report_email_service import (
    ReportEmailDeliveryError,
    TransactionImportReportEmailService,
)


class TransactionImportReportEmailServiceTest(TestCase):
    def setUp(self):
        self.user = User.objects.create_user(
            username="owner",
            password="pass123",
            email="owner@example.com",
            first_name="Caio",
        )
        self.account = Account.objects.create(
            owner=self.user,
            name="Checking",
            slug="checking",
        )
        self.category = Category.objects.create(
            owner=self.user,
            name="General",
            slug="general",
        )
        self.transaction_import = TransactionImport.objects.create(
            owner=self.user,
            source=TransactionImport.ImportSource.OFX,
            status=TransactionImport.ImportStatus.COMPLETED,
            report_email_status=TransactionImport.ReportEmailStatus.SCHEDULED,
        )

    def create_item(self, kind, amount, review_status):
        transaction = None
        if review_status == TransactionImportItem.ReviewStatus.APPROVED:
            transaction = Transaction.objects.create(
                owner=self.user,
                kind_of_transaction=kind,
                amount=amount,
                date=timezone.now(),
                description="Imported transaction",
                category=self.category,
                account=self.account,
            )

        return TransactionImportItem.objects.create(
            owner=self.user,
            transaction_import=self.transaction_import,
            transaction=transaction,
            kind_of_transaction=kind,
            amount=amount,
            date=timezone.now(),
            description="Imported transaction",
            account=self.account,
            suggested_category=self.category,
            review_status=review_status,
        )

    def test_sends_aggregate_report_once(self):
        self.create_item(Transaction.KindOfTransaction.INCOME, Decimal("500.00"), "APPROVED")
        self.create_item(Transaction.KindOfTransaction.EXPENSE, Decimal("125.50"), "APPROVED")
        self.create_item(Transaction.KindOfTransaction.EXPENSE, Decimal("40.00"), "REJECTED")
        service = TransactionImportReportEmailService()

        sent = service.send(self.transaction_import.id)
        sent_again = service.send(self.transaction_import.id)

        self.assertTrue(sent)
        self.assertFalse(sent_again)
        self.assertEqual(len(mail.outbox), 1)
        self.assertEqual(mail.outbox[0].to, ["owner@example.com"])
        self.assertIn(f"#{self.transaction_import.id}", mail.outbox[0].subject)
        self.assertIn("Approved transactions: 2", mail.outbox[0].body)
        self.assertIn("Total expenses: 125.50", mail.outbox[0].body)
        self.assertIn("Balance: 374.50", mail.outbox[0].body)
        self.assertIn("aggregate totals only", mail.outbox[0].body)
        self.assertEqual(
            mail.outbox[0].extra_headers["X-Idempotency-Key"],
            f"transaction-import-report-{self.transaction_import.id}",
        )
        self.assertEqual(
            mail.outbox[0].extra_headers["X-Mock-Email-Provider"],
            "resend",
        )
        self.assertIn('html lang="en" dir="ltr"', mail.outbox[0].alternatives[0][0])
        self.transaction_import.refresh_from_db()
        self.assertEqual(
            self.transaction_import.report_email_status,
            TransactionImport.ReportEmailStatus.SENT,
        )
        self.assertEqual(self.transaction_import.report_email_attempts, 1)
        self.assertEqual(self.transaction_import.report_email_provider, "resend")
        self.assertTrue(
            self.transaction_import.report_email_message_id.startswith("mock-resend-")
        )

    @override_settings(TRANSACTION_EMAIL_PROVIDER="mock_mailgun")
    def test_can_switch_to_mock_mailgun_without_changing_service(self):
        sent = TransactionImportReportEmailService().send(self.transaction_import.id)

        self.assertTrue(sent)
        self.assertEqual(
            mail.outbox[0].extra_headers["X-Mock-Email-Provider"],
            "mailgun",
        )
        self.transaction_import.refresh_from_db()
        self.assertEqual(self.transaction_import.report_email_provider, "mailgun")
        self.assertTrue(
            self.transaction_import.report_email_message_id.startswith("mock-mailgun-")
        )

    def test_skips_user_without_email(self):
        self.user.email = ""
        self.user.save(update_fields=["email"])

        sent = TransactionImportReportEmailService().send(self.transaction_import.id)

        self.assertFalse(sent)
        self.assertEqual(len(mail.outbox), 0)
        self.transaction_import.refresh_from_db()
        self.assertEqual(
            self.transaction_import.report_email_status,
            TransactionImport.ReportEmailStatus.SKIPPED,
        )

    @patch(
        "finances.transaction_imports.email_providers."
        "django_backend_mock_provider.EmailMultiAlternatives.send"
    )
    def test_marks_failure_for_celery_retry(self, send):
        send.side_effect = RuntimeError("provider unavailable")

        with self.assertRaises(ReportEmailDeliveryError):
            TransactionImportReportEmailService().send(self.transaction_import.id)

        self.transaction_import.refresh_from_db()
        self.assertEqual(
            self.transaction_import.report_email_status,
            TransactionImport.ReportEmailStatus.FAILED,
        )
        self.assertEqual(self.transaction_import.report_email_attempts, 1)
        self.assertIn("provider unavailable", self.transaction_import.report_email_error)
