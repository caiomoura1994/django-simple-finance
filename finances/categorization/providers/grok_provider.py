from .keyword_mock_provider import KeywordMockCategorizationProvider


class MockGrokCategorizationProvider(KeywordMockCategorizationProvider):
    provider_name = "Grok"
    confidence = 0.90
