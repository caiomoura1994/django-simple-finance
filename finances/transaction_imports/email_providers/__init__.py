from .contracts import (
    EmailDeliveryReceipt,
    EmailMessagePayload,
    TransactionEmailProvider,
)
from .factory import get_transaction_email_provider
from .mailgun_provider import MockMailgunEmailProvider
from .resend_provider import MockResendEmailProvider

__all__ = [
    "EmailDeliveryReceipt",
    "EmailMessagePayload",
    "MockMailgunEmailProvider",
    "MockResendEmailProvider",
    "TransactionEmailProvider",
    "get_transaction_email_provider",
]
