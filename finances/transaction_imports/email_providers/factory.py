from django.conf import settings
from django.utils.module_loading import import_string

from .contracts import TransactionEmailProvider
from .mailgun_provider import MockMailgunEmailProvider
from .resend_provider import MockResendEmailProvider


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
