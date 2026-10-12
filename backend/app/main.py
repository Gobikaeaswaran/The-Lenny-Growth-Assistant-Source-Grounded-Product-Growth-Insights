import json
import logging
from contextlib import asynccontextmanager

from fastapi import Depends, FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import JSONResponse, StreamingResponse
from sqlalchemy import select, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.agent import respond, token_chunks
from app.artifacts import sanitize_html
from app.config import get_settings
from app.db import engine, get_db
from app.models import Base, ChatSession, Message
from app.providers import LLMProviderFactory, ProviderUnavailable
from app.rag import ingest_transcripts
from app.schemas import ChatRequest, IngestRequest, MessageResponse, SessionCreate, SessionResponse

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("lenny-growth-assistant")


@asynccontextmanager
async def lifespan(_: FastAPI):
    try:
        async with engine.begin() as connection:
            if connection.dialect.name == "postgresql":
                await connection.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            await connection.run_sync(Base.metadata.create_all)
        logger.info("Database schema ready")
    except SQLAlchemyError:
        logger.exception("Database initialization failed; API remains available for health reporting")
    yield
    await engine.dispose()


app = FastAPI(title="The Lenny Growth Assistant API", version="1.0.0", lifespan=lifespan)
app.add_middleware(
    CORSMiddleware,
    allow_origins=get_settings().allowed_origins,
    allow_credentials=False,
    allow_methods=["GET", "POST", "OPTIONS"],
    allow_headers=["Content-Type"],
)


@app.get("/health")
async def health(db: AsyncSession = Depends(get_db)):
    try:
        await db.execute(text("SELECT 1"))
        database_status = "connected"
    except SQLAlchemyError as error:
        database_status = "unavailable"
        logger.warning("Health DB probe failed: %s", error.__class__.__name__)
    providers = await LLMProviderFactory.status()
    status = "ok" if database_status == "connected" else "degraded"
    return JSONResponse(
        status_code=200 if status == "ok" else 503,
        content={"status": status, "database": database_status, "providers": providers},
    )


@app.get("/api/sessions", response_model=list[SessionResponse])
async def list_sessions(db: AsyncSession = Depends(get_db)):
    sessions = (await db.scalars(
        select(ChatSession).order_by(ChatSession.updated_at.desc()).limit(100)
    )).all()
    return sessions


@app.post("/api/sessions", response_model=SessionResponse, status_code=201)
async def create_session(payload: SessionCreate, db: AsyncSession = Depends(get_db)):
    session = ChatSession(title=payload.title)
    db.add(session)
    await db.commit()
    await db.refresh(session)
    return session


@app.get("/api/sessions/{session_id}/messages", response_model=list[MessageResponse])
async def get_messages(session_id: str, db: AsyncSession = Depends(get_db)):
    session = await db.scalar(
        select(ChatSession).where(ChatSession.id == session_id).options(selectinload(ChatSession.messages))
    )
    if session is None:
        raise HTTPException(status_code=404, detail="Session not found")
    return [
        MessageResponse(
            id=message.id,
            role=message.role,
            content=message.content,
            citations=message.metadata_json.get("citations", []),
        )
        for message in session.messages
    ]


@app.post("/api/ingest")
async def ingest(payload: IngestRequest, db: AsyncSession = Depends(get_db)):
    try:
        count = await ingest_transcripts(db, payload.transcripts)
    except SQLAlchemyError as error:
        await db.rollback()
        logger.exception("Transcript ingestion failed")
        raise HTTPException(status_code=503, detail="Transcript indexing failed") from error
    return {"indexed_chunks": count, "transcripts": len(payload.transcripts)}


@app.post("/api/chat")
async def chat(payload: ChatRequest, db: AsyncSession = Depends(get_db)):
    try:
        answer, citations, artifact, provider = await respond(db, payload)
    except ValueError as error:
        raise HTTPException(status_code=404, detail=str(error)) from error
    except ProviderUnavailable as error:
        if not payload.stream:
            raise HTTPException(status_code=503, detail=str(error)) from error
        message = str(error)

        async def failure_event():
            data = json.dumps({"type": "error", "message": message})
            yield f"data: {data}\n\n"

        return StreamingResponse(failure_event(), media_type="text/event-stream")
    except SQLAlchemyError as error:
        await db.rollback()
        logger.exception("Chat database operation failed")
        raise HTTPException(status_code=503, detail="Conversation storage is unavailable") from error

    if artifact is not None and artifact.type == "html":
        artifact.content = sanitize_html(artifact.content)

    if not payload.stream:
        return {"answer": answer, "citations": citations, "artifact": artifact, "provider": provider}

    async def events():
        for token in token_chunks(answer):
            yield f"data: {json.dumps({'type': 'token', 'text': token})}\n\n"
        yield f"data: {json.dumps({'type': 'citations', 'citations': citations})}\n\n"
        if artifact is not None:
            yield f"data: {json.dumps({'type': 'artifact', 'artifact': artifact.model_dump()})}\n\n"
        yield f"data: {json.dumps({'type': 'done', 'provider': provider})}\n\n"

    return StreamingResponse(events(), media_type="text/event-stream", headers={"Cache-Control": "no-cache", "X-Accel-Buffering": "no"})