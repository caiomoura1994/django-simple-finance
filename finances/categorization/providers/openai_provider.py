from .keyword_mock_provider import KeywordMockCategorizationProvider


class MockOpenAICategorizationProvider(KeywordMockCategorizationProvider):
    provider_name = "OpenAI"
    confidence = 0.94
