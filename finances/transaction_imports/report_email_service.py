from dataclasses import dataclass
from decimal import Decimal

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.db import transaction as database_transaction
from django.db.models import Sum
from django.template.loader import render_to_string
from django.utils import timezone

from finances.models import Transaction, TransactionImport, TransactionImportItem


class ReportEmailDeliveryError(Exception):
    """Raised when the email backend cannot deliver an import report."""


@dataclass(frozen=True)
class TransactionImportReport:
    approved_count: int
    rejected_count: int
    total_income: Decimal
    total_expenses: Decimal

    @property
    def balance(self) -> Decimal:
        return self.total_income - self.total_expenses


class TransactionImportReportEmailService:
    """Build and send a minimal, aggregate-only financial import report."""

    def send(self, import_id: int) -> bool:
        transaction_import = self._claim_delivery(import_id)
        if transaction_import is None:
            return False

        recipient = transaction_import.owner.email
        if not recipient:
            self._mark_skipped(transaction_import, "The user does not have an email address.")
            return False

        report = self._build_report(transaction_import)
        context = {
            "transaction_import": transaction_import,
            "report": report,
            "recipient_name": transaction_import.owner.first_name
            or transaction_import.owner.username,
        }
        subject = f"Transaction import #{transaction_import.id} completed"
        text_body = render_to_string(
            "finances/emails/transaction_import_report.txt",
            context,
        )
        html_body = render_to_string(
            "finances/emails/transaction_import_report.html",
            context,
        )
        message = EmailMultiAlternatives(
            subject=subject,
            body=text_body,
            from_email=settings.DEFAULT_FROM_EMAIL,
            to=[recipient],
            reply_to=[settings.SUPPORT_EMAIL],
            headers={
                "X-Idempotency-Key": f"transaction-import-report-{transaction_import.id}"
            },
        )
        message.attach_alternative(html_body, "text/html")

        try:
            message.send(fail_silently=False)
        except Exception as exc:
            self._mark_failed(transaction_import, str(exc))
            raise ReportEmailDeliveryError(str(exc)) from exc

        transaction_import.report_email_status = TransactionImport.ReportEmailStatus.SENT
        transaction_import.report_email_sent_at = timezone.now()
        transaction_import.report_email_error = ""
        transaction_import.save(
            update_fields=[
                "report_email_status",
                "report_email_sent_at",
                "report_email_error",
                "updated_at",
            ]
        )
        return True

    @staticmethod
    def _claim_delivery(import_id):
        with database_transaction.atomic():
            transaction_import = (
                TransactionImport.objects.select_for_update()
                .select_related("owner")
                .get(pk=import_id)
            )
            if transaction_import.report_email_status in {
                TransactionImport.ReportEmailStatus.SENDING,
                TransactionImport.ReportEmailStatus.SENT,
                TransactionImport.ReportEmailStatus.SKIPPED,
            }:
                return None

            transaction_import.report_email_status = (
                TransactionImport.ReportEmailStatus.SENDING
            )
            transaction_import.report_email_attempts += 1
            transaction_import.save(
                update_fields=[
                    "report_email_status",
                    "report_email_attempts",
                    "updated_at",
                ]
            )
            return transaction_import

    @staticmethod
    def _build_report(transaction_import):
        items = TransactionImportItem.objects.filter(transaction_import=transaction_import)
        approved_items = items.filter(
            review_status=TransactionImportItem.ReviewStatus.APPROVED
        )
        income = approved_items.filter(
            kind_of_transaction=Transaction.KindOfTransaction.INCOME
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")
        expenses = approved_items.filter(
            kind_of_transaction=Transaction.KindOfTransaction.EXPENSE
        ).aggregate(total=Sum("amount"))["total"] or Decimal("0.00")

        return TransactionImportReport(
            approved_count=approved_items.count(),
            rejected_count=items.filter(
                review_status=TransactionImportItem.ReviewStatus.REJECTED
            ).count(),
            total_income=income,
            total_expenses=expenses,
        )

    @staticmethod
    def _mark_skipped(transaction_import, reason):
        transaction_import.report_email_status = TransactionImport.ReportEmailStatus.SKIPPED
        transaction_import.report_email_error = reason
        transaction_import.save(
            update_fields=["report_email_status", "report_email_error", "updated_at"]
        )

    @staticmethod
    def _mark_failed(transaction_import, error):
        transaction_import.report_email_status = TransactionImport.ReportEmailStatus.FAILED
        transaction_import.report_email_error = error[:2000]
        transaction_import.save(
            update_fields=["report_email_status", "report_email_error", "updated_at"]
        )
