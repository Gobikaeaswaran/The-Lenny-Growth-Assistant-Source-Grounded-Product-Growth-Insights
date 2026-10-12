import hashlib
import re
from dataclasses import dataclass

from sqlalchemy import delete, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import get_settings
from app.embeddings import embed_text
from app.models import TranscriptChunk
from app.schemas import TranscriptInput

STOP_WORDS = frozenset({
    "a", "about", "an", "and", "are", "as", "at", "be", "by", "do", "does", "for", "from",
    "how", "i", "in", "is", "it", "me", "of", "on", "or", "that", "the", "this", "to", "was",
    "what", "when", "where", "which", "who", "why", "with", "you",
})
CONCEPT_ALIASES = {
    "product market fit": frozenset({
        "customer", "customers", "segment", "segments", "user", "users", "interview", "interviews",
        "interviewed", "interviewees", "workaround", "workarounds", "pain", "painful", "handoffs",
        "workflow", "assumptions", "evidence", "repeat", "repeated", "weekly", "use", "usage",
        "retention", "invited", "referrals",
    }),
}


def content_terms(text: str) -> set[str]:
    return set(re.findall(r"[a-z0-9]+", text.lower())) - STOP_WORDS


def relevance_score(query: str, candidate: str) -> float:
    query_terms = content_terms(query)
    candidate_terms = content_terms(candidate)
    if not query_terms:
        return 0.0
    scores = [len(query_terms & candidate_terms) / len(query_terms)]
    normalized_query = " ".join(re.findall(r"[a-z0-9]+", query.lower()))
    for phrase, aliases in CONCEPT_ALIASES.items():
        if phrase in normalized_query:
            scores.append(min(len(aliases & candidate_terms) / 3, 1.0))
    return max(scores)


@dataclass
class SearchResult:
    chunk: TranscriptChunk
    score: float


def split_text(text: str, chunk_tokens: int | None = None, overlap: int | None = None) -> list[str]:
    words = text.split()
    size = chunk_tokens or get_settings().chunk_tokens
    overlap_size = overlap if overlap is not None else get_settings().chunk_overlap
    if size < 1 or overlap_size < 0 or overlap_size >= size:
        raise ValueError("Chunk size must be positive and overlap must be smaller than chunk size")
    chunks = []
    start = 0
    while start < len(words):
        end = min(start + size, len(words))
        chunks.append(" ".join(words[start:end]))
        if end == len(words):
            break
        start = end - overlap_size
    return chunks


async def ingest_transcripts(db: AsyncSession, transcripts: list[TranscriptInput]) -> int:
    count = 0
    for transcript in transcripts:
        chunks = split_text(transcript.content)
        source_key = f"{transcript.title}\0{transcript.url or ''}"
        source_id = hashlib.sha256(source_key.encode("utf-8")).hexdigest()[:32]
        await db.execute(delete(TranscriptChunk).where(TranscriptChunk.source_id == source_id))
        db.add_all([
            TranscriptChunk(
                source_id=source_id,
                title=transcript.title,
                speaker=transcript.speaker,
                timestamp=transcript.timestamp,
                url=transcript.url,
                content=content,
                chunk_index=index,
                embedding=embed_text(content),
            )
            for index, content in enumerate(chunks)
        ])
        count += len(chunks)
    await db.commit()
    return count


async def search_transcripts(db: AsyncSession, query: str, limit: int = 5) -> list[SearchResult]:
    query_terms = content_terms(query)
    if not query_terms:
        return []
    query_vector = embed_text(query)
    dialect = db.bind.dialect.name if db.bind is not None else "sqlite"
    if dialect == "postgresql":
        candidates = (await db.scalars(
            select(TranscriptChunk)
            .order_by(TranscriptChunk.embedding.cosine_distance(query_vector))
            .limit(limit * 5)
        )).all()
    else:
        candidates = (await db.scalars(select(TranscriptChunk))).all()

    scored = []
    for chunk in candidates:
        terms = content_terms(chunk.content)
        overlap_score = relevance_score(query, chunk.content)
        cosine_similarity = sum(left * right for left, right in zip(query_vector, chunk.embedding))
        score = max(overlap_score, cosine_similarity)
        if overlap_score >= 0.15 or cosine_similarity >= 0.3:
            scored.append(SearchResult(chunk, score))
    return sorted(scored, key=lambda result: result.score, reverse=True)[:limit]