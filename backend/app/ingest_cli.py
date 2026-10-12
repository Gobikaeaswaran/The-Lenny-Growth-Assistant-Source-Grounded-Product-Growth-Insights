import asyncio
import json
from pathlib import Path

from app.db import SessionFactory, engine
from app.models import Base
from app.rag import ingest_transcripts
from app.schemas import TranscriptInput


async def main() -> None:
    source = Path("data/demo_transcripts.json")
    documents = json.loads(source.read_text(encoding="utf-8"))
    async with engine.begin() as connection:
        if connection.dialect.name == "postgresql":
            await connection.execute(__import__("sqlalchemy").text("CREATE EXTENSION IF NOT EXISTS vector"))
        await connection.run_sync(Base.metadata.create_all)
    async with SessionFactory() as db:
        count = await ingest_transcripts(db, [TranscriptInput(**document) for document in documents])
    print(f"Indexed {count} chunks from {len(documents)} synthetic demo transcript(s).")
    await engine.dispose()


if __name__ == "__main__":
    asyncio.run(main())