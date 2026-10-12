from typing import Literal

from pydantic import BaseModel, ConfigDict, Field


class SessionCreate(BaseModel):
    title: str = Field(default="New conversation", min_length=1, max_length=200)


class SessionResponse(BaseModel):
    model_config = ConfigDict(from_attributes=True)

    id: str
    title: str


class MessageResponse(BaseModel):
    id: str
    role: str
    content: str
    citations: list[dict] = Field(default_factory=list)


class ChatRequest(BaseModel):
    session_id: str
    message: str = Field(min_length=1, max_length=12000)
    model: Literal["ollama", "anthropic"] = "ollama"
    mode: Literal["quote", "answer", "essay", "artifact"] = "quote"
    stream: bool = True


class TranscriptInput(BaseModel):
    title: str = Field(min_length=1, max_length=400)
    speaker: str = Field(default="Unknown", max_length=200)
    content: str = Field(min_length=1, max_length=1000000)
    url: str | None = None
    timestamp: str | None = None


class IngestRequest(BaseModel):
    transcripts: list[TranscriptInput] = Field(min_length=1, max_length=100)


class Artifact(BaseModel):
    type: Literal["markdown", "html", "code"]
    title: str
    content: str