"""The complete transaction-import workflow, kept in one readable place."""

import os
from dataclasses import dataclass

from django.db import transaction as database_transaction
from django.db.models import F
from django.utils import timezone
from loguru import logger

from finances.categorization import CategorizationService
from finances.models import (
    TransactionCategoryRule,
    TransactionImport,
    TransactionImportItem,
)

from .processors import ProcessorFactory


@dataclass(frozen=True)
class ImportOutcome:
    total_items: int
    approved_items: int
    pending_review_items: int

    @property
    def needs_human_review(self) -> bool:
        return self.pending_review_items > 0


class TransactionImportOrchestrator:
    """Parse, categorize, route for review, persist, and notify the user."""

    ASSISTED_SOURCES = {
        TransactionImport.ImportSource.OFX,
        TransactionImport.ImportSource.IMAGE,
    }

    def __init__(
        self,
        categorization_service=None,
        processor_factory=None,
        report_dispatcher=None,
    ):
        self.categorization = categorization_service
        self.processor_factory = processor_factory or ProcessorFactory
        self.report_dispatcher = report_dispatcher or self._dispatch_report_email

    def run(self, import_id: int) -> ImportOutcome:
        """Execute the whole automatic portion of an import."""

        transaction_import = TransactionImport.objects.select_related("owner").get(
            pk=import_id
        )
        file_path = None

        try:
            self._mark_processing(transaction_import)
            file_path = transaction_import.file.path

            # 1. Deterministic parsing: amounts, dates and descriptions never use AI.
            transactions = self._parse_file(transaction_import, file_path)

            rule_decisions = {}
            ai_decisions = {}
            if transaction_import.source in self.ASSISTED_SOURCES:
                categorization = self.categorization or CategorizationService()

                # 2. Deterministic learned rules run before any external provider.
                rule_decisions = categorization.apply_learned_rules(
                    transactions,
                    transaction_import.owner,
                )

                # 3. AI receives only entries that no learned rule resolved.
                ai_decisions = categorization.suggest_with_ai(
                    transactions,
                    transaction_import.owner,
                    resolved_indices=set(rule_decisions),
                )
            decisions = {**rule_decisions, **ai_decisions}

            # 4. Learned rules are trusted; new/AI choices become human-review drafts.
            outcome = self._persist_or_delegate(
                transaction_import,
                transactions,
                decisions,
            )

            # 5. No pending human work means the import can finish and email a report.
            if outcome.needs_human_review:
                self._mark_awaiting_review(transaction_import)
            else:
                self._complete_and_schedule_report(transaction_import)

            return outcome
        except Exception as exc:
            self._mark_failed(transaction_import, exc)
            raise
        finally:
            self._remove_uploaded_file(file_path)

    def resume_after_human_review(self, import_id: int) -> bool:
        """Complete and notify after the final draft is approved or rejected."""

        transaction_import = TransactionImport.objects.get(pk=import_id)
        has_pending_items = transaction_import.items.filter(
            review_status=TransactionImportItem.ReviewStatus.PENDING_REVIEW
        ).exists()
        if has_pending_items:
            return False

        self._complete_and_schedule_report(transaction_import)
        return True

    @staticmethod
    def _mark_processing(transaction_import):
        transaction_import.status = TransactionImport.ImportStatus.PROCESSING
        transaction_import.processed_items = 0
        transaction_import.error_message = ""
        transaction_import.save(
            update_fields=["status", "processed_items", "error_message", "updated_at"]
        )

    def _parse_file(self, transaction_import, file_path):
        file_extension = os.path.splitext(file_path)[1]
        processor = self.processor_factory.get_processor(file_extension)
        return processor.process(file_path, transaction_import.owner)

    @database_transaction.atomic
    def _persist_or_delegate(self, transaction_import, transactions, decisions):
        approved_items = 0
        pending_review_items = 0

        for index, parsed_transaction in enumerate(transactions):
            decision = decisions.get(index)
            suggested_category = (
                decision.category if decision else parsed_transaction.category
            )
            source = (
                decision.source
                if decision
                else TransactionImportItem.CategorizationSource.IMPORT
            )
            requires_review = (
                transaction_import.source in self.ASSISTED_SOURCES
                and source != TransactionImportItem.CategorizationSource.RULE
            )

            saved_transaction = None
            review_status = TransactionImportItem.ReviewStatus.PENDING_REVIEW
            if requires_review:
                pending_review_items += 1
            else:
                parsed_transaction.category = suggested_category
                parsed_transaction.save()
                saved_transaction = parsed_transaction
                review_status = TransactionImportItem.ReviewStatus.APPROVED
                approved_items += 1

                if decision and decision.rule:
                    TransactionCategoryRule.objects.filter(pk=decision.rule.pk).update(
                        times_applied=F("times_applied") + 1,
                        last_used_at=timezone.now(),
                    )

            TransactionImportItem.objects.create(
                owner=transaction_import.owner,
                transaction_import=transaction_import,
                transaction=saved_transaction,
                kind_of_transaction=parsed_transaction.kind_of_transaction,
                amount=parsed_transaction.amount,
                date=parsed_transaction.date,
                description=parsed_transaction.description,
                account=parsed_transaction.account,
                suggested_category=suggested_category,
                categorization_source=source,
                review_status=review_status,
                ai_confidence=decision.confidence if decision else None,
                ai_reasoning=decision.reasoning if decision else "",
                reviewed_at=timezone.now() if saved_transaction else None,
            )

        transaction_import.total_items = len(transactions)
        transaction_import.processed_items = len(transactions)
        transaction_import.save(
            update_fields=["total_items", "processed_items", "updated_at"]
        )
        return ImportOutcome(
            total_items=len(transactions),
            approved_items=approved_items,
            pending_review_items=pending_review_items,
        )

    @staticmethod
    def _mark_awaiting_review(transaction_import):
        transaction_import.status = TransactionImport.ImportStatus.AWAITING_REVIEW
        transaction_import.save(update_fields=["status", "updated_at"])

    def _complete_and_schedule_report(self, transaction_import):
        transaction_import.status = TransactionImport.ImportStatus.COMPLETED
        should_schedule = transaction_import.report_email_status in {
            TransactionImport.ReportEmailStatus.NOT_SCHEDULED,
            TransactionImport.ReportEmailStatus.FAILED,
        }
        if should_schedule:
            transaction_import.report_email_status = (
                TransactionImport.ReportEmailStatus.SCHEDULED
            )
        transaction_import.save(
            update_fields=["status", "report_email_status", "updated_at"]
        )

        if should_schedule:
            self.report_dispatcher(transaction_import.id)

    @staticmethod
    def _dispatch_report_email(import_id):
        from .tasks import send_transaction_import_report

        database_transaction.on_commit(
            lambda: send_transaction_import_report.delay(import_id)
        )

    @staticmethod
    def _mark_failed(transaction_import, error):
        transaction_import.status = TransactionImport.ImportStatus.FAILED
        transaction_import.error_message = str(error)
        transaction_import.save(
            update_fields=["status", "error_message", "updated_at"]
        )
        logger.error(
            "Transaction import {} failed: {}",
            transaction_import.id,
            str(error),
        )

    @staticmethod
    def _remove_uploaded_file(file_path):
        if file_path and os.path.exists(file_path):
            os.remove(file_path)
