import pytest
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine

from app.embeddings import embed_text
from app.models import Base, TranscriptChunk
from app.rag import ingest_transcripts, search_transcripts, split_text
from app.schemas import TranscriptInput


def test_chunker_preserves_overlap_and_all_content():
    chunks = split_text("one two three four five six seven", chunk_tokens=4, overlap=1)
    assert chunks == ["one two three four", "four five six seven"]


def test_embedding_is_normalized_and_deterministic():
    first = embed_text("customer interviews and product growth")
    assert first == embed_text("customer interviews and product growth")
    assert sum(value * value for value in first) == pytest.approx(1.0)


@pytest.mark.asyncio
async def test_ingestion_and_retrieval_rank_matching_source():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        documents = [
            TranscriptInput(title="Customer interviews", speaker="Founder", content="customer interviews validate user pain and product assumptions"),
            TranscriptInput(title="Growth loops", speaker="Growth lead", content="growth loops connect product value, referrals and activation"),
        ]
        assert await ingest_transcripts(db, documents) == 2
        assert await ingest_transcripts(db, documents) == 2
        assert await db.scalar(select(func.count()).select_from(TranscriptChunk)) == 2
        results = await search_transcripts(db, "customer interviews validate product", limit=2)
        assert results[0].chunk.title == "Customer interviews"
        assert results[0].chunk.speaker == "Founder"
    await engine.dispose()


@pytest.mark.asyncio
async def test_retrieval_rejects_unrelated_source():
    engine = create_async_engine("sqlite+aiosqlite:///:memory:")
    async with engine.begin() as connection:
        await connection.run_sync(Base.metadata.create_all)
    factory = async_sessionmaker(engine, expire_on_commit=False)
    async with factory() as db:
        await ingest_transcripts(db, [
            TranscriptInput(title="Deployment guide", content="Feature flags make deployment and rollback safer for engineering teams."),
        ])
        results = await search_transcripts(db, "How do founders find product market fit?")
        assert results == []
    await engine.dispose()