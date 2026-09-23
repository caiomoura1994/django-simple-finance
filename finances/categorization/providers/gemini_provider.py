from .keyword_mock_provider import KeywordMockCategorizationProvider


class MockGeminiCategorizationProvider(KeywordMockCategorizationProvider):
    provider_name = "Gemini"
    confidence = 0.92
