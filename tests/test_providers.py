import pytest

from app.config import get_settings
from app.providers import LLMProviderFactory, ProviderReply, ProviderUnavailable


@pytest.mark.asyncio
async def test_provider_factory_falls_back_from_ollama(monkeypatch):
    class LocalProvider:
        async def generate(self, _messages):
            raise ProviderUnavailable("Ollama is offline")

    class CloudProvider:
        async def generate(self, _messages):
            return ProviderReply("Recovered response", "anthropic", "claude-test")

    settings = get_settings()
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    providers = {"ollama": LocalProvider(), "anthropic": CloudProvider()}
    monkeypatch.setattr(LLMProviderFactory, "configured", staticmethod(lambda name: providers[name]))

    reply = await LLMProviderFactory.generate([{"role": "user", "content": "hello"}], preferred="ollama")

    assert reply.provider == "anthropic"
    assert reply.text == "Recovered response"


@pytest.mark.asyncio
async def test_provider_factory_returns_structured_unavailable_when_all_fail(monkeypatch):
    class FailedProvider:
        async def generate(self, _messages):
            raise ProviderUnavailable("Provider offline")

    settings = get_settings()
    monkeypatch.setattr(settings, "anthropic_api_key", "test-key")
    monkeypatch.setattr(LLMProviderFactory, "configured", staticmethod(lambda _name: FailedProvider()))

    with pytest.raises(ProviderUnavailable, match="No language model is available"):
        await LLMProviderFactory.generate([], preferred="ollama")
