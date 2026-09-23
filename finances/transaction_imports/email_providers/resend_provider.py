from .django_backend_mock_provider import DjangoBackendMockEmailProvider


class MockResendEmailProvider(DjangoBackendMockEmailProvider):
    provider_name = "resend"
