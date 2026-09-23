from celery import shared_task

from .orchestrator import TransactionImportOrchestrator
from .report_email_service import (
    ReportEmailDeliveryError,
    TransactionImportReportEmailService,
)


@shared_task
def process_transaction_import(import_id):
    TransactionImportOrchestrator().run(import_id)


@shared_task(bind=True, max_retries=3)
def send_transaction_import_report(self, import_id):
    try:
        TransactionImportReportEmailService().send(import_id)
    except ReportEmailDeliveryError as exc:
        countdown = min(2 ** self.request.retries, 30)
        raise self.retry(exc=exc, countdown=countdown)
