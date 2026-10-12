from dataclasses import dataclass

import httpx

from app.config import get_settings


class ProviderUnavailable(Exception):
    pass


@dataclass
class ProviderReply:
    text: str
    provider: str
    model: str


class OllamaProvider:
    async def generate(self, messages: list[dict[str, str]]) -> ProviderReply:
        settings = get_settings()
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            response = await client.post(
                f"{settings.ollama_base_url.rstrip('/')}/api/chat",
                json={"model": settings.ollama_model, "messages": messages, "stream": False},
            )
            response.raise_for_status()
        text = response.json().get("message", {}).get("content", "").strip()
        if not text:
            raise ProviderUnavailable("Ollama returned an empty response")
        return ProviderReply(text, "ollama", settings.ollama_model)


class AnthropicProvider:
    async def generate(self, messages: list[dict[str, str]]) -> ProviderReply:
        settings = get_settings()
        if not settings.anthropic_api_key:
            raise ProviderUnavailable("Anthropic is not configured; set ANTHROPIC_API_KEY to enable cloud fallback")
        system = "\n\n".join(item["content"] for item in messages if item["role"] == "system")
        conversation = [item for item in messages if item["role"] != "system"]
        async with httpx.AsyncClient(timeout=settings.provider_timeout_seconds) as client:
            response = await client.post(
                "https://api.anthropic.com/v1/messages",
                headers={"x-api-key": settings.anthropic_api_key, "anthropic-version": "2023-06-01"},
                json={"model": settings.anthropic_model, "max_tokens": 1600, "system": system, "messages": conversation},
            )
            response.raise_for_status()
        text = "".join(block.get("text", "") for block in response.json().get("content", []) if block.get("type") == "text").strip()
        if not text:
            raise ProviderUnavailable("Anthropic returned an empty response")
        return ProviderReply(text, "anthropic", settings.anthropic_model)


class LLMProviderFactory:
    @staticmethod
    def configured(name: str):
        if name == "ollama":
            return OllamaProvider()
        if name == "anthropic":
            return AnthropicProvider()
        raise ValueError(f"Unsupported provider: {name}")

    @classmethod
    async def generate(cls, messages: list[dict[str, str]], preferred: str | None = None) -> ProviderReply:
        settings = get_settings()
        requested = preferred or settings.default_model
        order = [requested, "anthropic" if requested == "ollama" else "ollama"]
        failures = []
        for provider_name in order:
            if provider_name == "anthropic" and not settings.anthropic_api_key:
                failures.append("anthropic: no API key configured")
                continue
            try:
                return await cls.configured(provider_name).generate(messages)
            except (httpx.HTTPError, ProviderUnavailable, TimeoutError) as error:
                failures.append(f"{provider_name}: {error}")
        raise ProviderUnavailable("No language model is available. " + "; ".join(failures))

    @classmethod
    async def status(cls) -> dict[str, str]:
        settings = get_settings()
        result = {"default": settings.default_model, "ollama": "unknown", "anthropic": "configured" if settings.anthropic_api_key else "not_configured"}
        try:
            async with httpx.AsyncClient(timeout=2) as client:
                response = await client.get(f"{settings.ollama_base_url.rstrip('/')}/api/tags")
                response.raise_for_status()
            result["ollama"] = "available"
        except httpx.HTTPError:
            result["ollama"] = "unavailable"
        return result