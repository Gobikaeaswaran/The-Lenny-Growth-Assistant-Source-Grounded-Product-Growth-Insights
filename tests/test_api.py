from unittest.mock import AsyncMock

import pytest

from app.main import LLMProviderFactory


@pytest.mark.asyncio
async def test_health_reports_database_and_provider_state(client, monkeypatch):
    monkeypatch.setattr(LLMProviderFactory, "status", AsyncMock(return_value={"default": "ollama", "ollama": "available", "anthropic": "not_configured"}))
    response = await client.get("/health")
    assert response.status_code == 200
    assert response.json()["database"] == "connected"
    assert response.json()["providers"]["ollama"] == "available"


@pytest.mark.asyncio
async def test_cors_allows_vite_loopback_origin(client):
    response = await client.options(
        "/api/sessions",
        headers={"Origin": "http://127.0.0.1:5173", "Access-Control-Request-Method": "GET"},
    )
    assert response.headers["access-control-allow-origin"] == "http://127.0.0.1:5173"


@pytest.mark.asyncio
async def test_session_creation_listing_and_messages(client):
    created = await client.post("/api/sessions", json={"title": "Research growth loops"})
    assert created.status_code == 201
    session_id = created.json()["id"]
    listed = await client.get("/api/sessions")
    assert any(item["id"] == session_id for item in listed.json())
    messages = await client.get(f"/api/sessions/{session_id}/messages")
    assert messages.status_code == 200
    assert messages.json() == []


@pytest.mark.asyncio
async def test_session_messages_include_persisted_chat(client, monkeypatch):
    from app.providers import ProviderReply

    session = await client.post("/api/sessions", json={"title": "Persisted messages"})
    monkeypatch.setattr(LLMProviderFactory, "generate", AsyncMock(return_value=ProviderReply("A grounded answer.", "ollama", "llama3.2")))
    await client.post("/api/chat", json={"session_id": session.json()["id"], "message": "What is growth?", "stream": False})

    messages = await client.get(f"/api/sessions/{session.json()['id']}/messages")
    assert messages.status_code == 200
    assert [item["role"] for item in messages.json()] == ["user", "assistant"]


@pytest.mark.asyncio
async def test_session_messages_returns_404_for_unknown_session(client):
    response = await client.get("/api/sessions/missing/messages")
    assert response.status_code == 404


@pytest.mark.asyncio
async def test_ingest_endpoint_indexes_transcripts(client):
    response = await client.post("/api/ingest", json={"transcripts": [{"title": "Test source", "speaker": "Guest", "content": "Customer interviews are useful for testing product assumptions."}]})
    assert response.status_code == 200
    assert response.json()["indexed_chunks"] == 1


@pytest.mark.asyncio
async def test_chat_reports_structured_provider_unavailable(client, monkeypatch):
    await client.post("/api/ingest", json={"transcripts": [{"title": "Source", "content": "How do teams grow?"}]})
    session = await client.post("/api/sessions", json={"title": "Test"})
    monkeypatch.setattr(LLMProviderFactory, "generate", AsyncMock(side_effect=__import__("app.providers", fromlist=["ProviderUnavailable"]).ProviderUnavailable("No models available")))
    response = await client.post("/api/chat", json={"session_id": session.json()["id"], "message": "How do teams grow?", "mode": "answer", "stream": False})
    assert response.status_code == 503
    assert "No models available" in response.json()["detail"]


@pytest.mark.asyncio
async def test_chat_abstains_when_retrieval_has_no_sources(client, monkeypatch):
    session = await client.post("/api/sessions", json={"title": "No sources"})
    generate = AsyncMock()
    monkeypatch.setattr(LLMProviderFactory, "generate", generate)

    response = await client.post("/api/chat", json={"session_id": session.json()["id"], "message": "Tell me about a topic absent from this library", "stream": False})

    assert response.status_code == 200
    assert response.json()["provider"] == "none"
    assert response.json()["citations"] == []
    assert "couldn't find a matching source" in response.json()["answer"]
    generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_streaming_chat_reports_provider_failure(client, monkeypatch):
    from app.providers import ProviderUnavailable

    await client.post("/api/ingest", json={"transcripts": [{"title": "Source", "content": "Help"}]})
    session = await client.post("/api/sessions", json={"title": "Streaming failure"})
    monkeypatch.setattr(LLMProviderFactory, "generate", AsyncMock(side_effect=ProviderUnavailable("No models available")))
    response = await client.post("/api/chat", json={"session_id": session.json()["id"], "message": "Help", "mode": "answer", "stream": True})

    assert response.status_code == 200
    assert '"type": "error"' in response.text
    assert "No models available" in response.text


@pytest.mark.asyncio
async def test_chat_returns_grounded_answer_and_citation(client, monkeypatch):
    await client.post("/api/ingest", json={"transcripts": [{"title": "Synthetic source", "speaker": "Guest", "timestamp": "00:01:00", "content": "The team validated customer pain through interviews and measured repeat usage."}]})
    session = await client.post("/api/sessions", json={"title": "Test"})
    monkeypatch.setattr(LLMProviderFactory, "generate", AsyncMock(return_value=__import__("app.providers", fromlist=["ProviderReply"]).ProviderReply("The team used interviews [Synthetic source, Guest].", "ollama", "llama3.2")))
    response = await client.post("/api/chat", json={"session_id": session.json()["id"], "message": "How did interviews help?", "stream": False})
    assert response.status_code == 200
    assert response.json()["citations"][0]["title"] == "Synthetic source"


@pytest.mark.asyncio
async def test_nonstreaming_html_artifact_is_sanitized(client, monkeypatch):
    from app.providers import ProviderReply

    await client.post("/api/ingest", json={"transcripts": [{"title": "Artifact request", "content": "Create a demo card"}]})
    session = await client.post("/api/sessions", json={"title": "Artifact"})
    malicious = '<div onclick="alert(1)">safe<script>alert(2)</script><a href="javascript:alert(3)">link</a></div>'
    monkeypatch.setattr(LLMProviderFactory, "generate", AsyncMock(return_value=ProviderReply(f"```html\n{malicious}\n```", "ollama", "llama3.2")))

    response = await client.post("/api/chat", json={"session_id": session.json()["id"], "message": "Create a demo card", "mode": "artifact", "stream": False})

    assert response.status_code == 200
    html = response.json()["artifact"]["content"]
    assert "<script" not in html.lower()
    assert "onclick" not in html.lower()
    assert "javascript:" not in html.lower()


@pytest.mark.asyncio
async def test_exact_mode_returns_verbatim_source_sentence_without_llm(client, monkeypatch):
    from app.providers import ProviderReply

    sentence = "A user creates a useful report, shares it with a teammate, and that teammate becomes a new active user."
    await client.post("/api/ingest", json={"transcripts": [{"title": "Growth loop interview", "speaker": "Guest", "timestamp": "00:08:15", "url": "https://example.com/interview", "content": sentence}]})
    session = await client.post("/api/sessions", json={"title": "Exact source"})
    generate = AsyncMock(return_value=ProviderReply("This should not be used.", "ollama", "llama3.2"))
    monkeypatch.setattr(LLMProviderFactory, "generate", generate)

    response = await client.post("/api/chat", json={"session_id": session.json()["id"], "message": "What happens when a user shares a report?", "mode": "quote", "stream": False})

    assert response.status_code == 200
    assert f"“{sentence}”" in response.json()["answer"]
    assert response.json()["citations"][0]["title"] == "Growth loop interview"
    assert response.json()["provider"] == "source"
    generate.assert_not_awaited()


@pytest.mark.asyncio
async def test_product_market_fit_question_uses_relevant_demo_sentence(client, monkeypatch):
    from app.providers import ProviderReply

    sentence = "The team measured repeated weekly use and whether customers invited a collaborator."
    content = f"This synthetic sample describes how a small software team found an initial customer segment. {sentence} This example is fabricated solely for local software demonstrations and is not a real podcast transcript or quotation."
    await client.post("/api/ingest", json={"transcripts": [{"title": "Synthetic Demo: Finding an Initial Customer Segment", "speaker": "Demo product founder", "timestamp": "00:12:40", "content": content}]})
    session = await client.post("/api/sessions", json={"title": "Exact product-market-fit source"})
    generate = AsyncMock(return_value=ProviderReply("Unused", "ollama", "llama3.2"))
    monkeypatch.setattr(LLMProviderFactory, "generate", generate)

    response = await client.post("/api/chat", json={"session_id": session.json()["id"], "message": "How do great teams find product-market fit?", "stream": False})

    assert response.status_code == 200
    assert f"“{sentence}”" in response.json()["answer"]
    assert "fabricated solely" not in response.json()["answer"]
    assert response.json()["citations"][0]["title"] == "Synthetic Demo: Finding an Initial Customer Segment"
    generate.assert_not_awaited()