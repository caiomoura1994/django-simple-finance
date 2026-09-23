from abc import ABC, abstractmethod
from dataclasses import dataclass


@dataclass(frozen=True)
class EmailMessagePayload:
    recipient: str
    subject: str
    text_body: str
    html_body: str
    from_email: str
    reply_to: str
    idempotency_key: str


@dataclass(frozen=True)
class EmailDeliveryReceipt:
    provider: str
    message_id: str


class TransactionEmailProvider(ABC):
    """Contract implemented by Resend, Mailgun, or another email adapter."""

    @abstractmethod
    def send(self, payload: EmailMessagePayload) -> EmailDeliveryReceipt:
        raise NotImplementedError
