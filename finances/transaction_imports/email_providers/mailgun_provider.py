from .django_backend_mock_provider import DjangoBackendMockEmailProvider


class MockMailgunEmailProvider(DjangoBackendMockEmailProvider):
    provider_name = "mailgun"
