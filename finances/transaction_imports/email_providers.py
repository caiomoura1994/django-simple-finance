from abc import ABC, abstractmethod
from dataclasses import dataclass
from hashlib import sha256

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils.module_loading import import_string


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


class DjangoBackendMockEmailProvider(TransactionEmailProvider):
    """Simulate a remote provider through Django's local email backend."""

    provider_name = "mock"

    def send(self, payload: EmailMessagePayload) -> EmailDeliveryReceipt:
        message = EmailMultiAlternatives(
            subject=payload.subject,
            body=payload.text_body,
            from_email=payload.from_email,
            to=[payload.recipient],
            reply_to=[payload.reply_to],
            headers={
                "X-Idempotency-Key": payload.idempotency_key,
                "X-Mock-Email-Provider": self.provider_name,
            },
        )
        message.attach_alternative(payload.html_body, "text/html")
        delivered = message.send(fail_silently=False)
        if delivered != 1:
            raise RuntimeError(f"Mock {self.provider_name} did not accept the email")

        digest = sha256(
            f"{self.provider_name}:{payload.idempotency_key}".encode("utf-8")
        ).hexdigest()[:16]
        return EmailDeliveryReceipt(
            provider=self.provider_name,
            message_id=f"mock-{self.provider_name}-{digest}",
        )


class MockResendEmailProvider(DjangoBackendMockEmailProvider):
    provider_name = "resend"


class MockMailgunEmailProvider(DjangoBackendMockEmailProvider):
    provider_name = "mailgun"


EMAIL_PROVIDER_ALIASES = {
    "mock_resend": MockResendEmailProvider,
    "mock_mailgun": MockMailgunEmailProvider,
}


def get_transaction_email_provider() -> TransactionEmailProvider:
    provider_reference = settings.TRANSACTION_EMAIL_PROVIDER
    provider_class = EMAIL_PROVIDER_ALIASES.get(provider_reference)
    if provider_class is None:
        provider_class = import_string(provider_reference)
    provider = provider_class()

    if not isinstance(provider, TransactionEmailProvider):
        raise TypeError(
            f"{provider_reference} must implement TransactionEmailProvider"
        )

    return provider
