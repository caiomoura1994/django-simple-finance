from hashlib import sha256

from django.core.mail import EmailMultiAlternatives

from .contracts import (
    EmailDeliveryReceipt,
    EmailMessagePayload,
    TransactionEmailProvider,
)


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
