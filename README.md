# The Lenny Growth Assistant

A local-first product and growth research assistant that finds relevant passages in an indexed transcript library. Its default Exact source mode quotes source text directly with citations; optional AI modes can generate answers, essays, and artifacts.

## Main Features

- **Exact source answers:** Returns up to three relevant transcript sentences verbatim with the source title, speaker, timestamp, and link. It abstains when it cannot find supporting text.
- **AI-assisted writing:** Optional answer, Ship 30 for 30 essay, and artifact modes use Ollama by default, with Anthropic as an optional fallback.
- **Transcript search:** Ingest authorized transcript text, split it into overlapping chunks, and retrieve relevant passages using PostgreSQL and pgvector.
- **Conversation history:** Create sessions and revisit saved messages and citations.
- **Artifact preview:** View generated HTML in a sandboxed iframe.

## Technology

- **Frontend:** React, TypeScript, Vite, and Lucide icons.
- **Backend:** Python 3.11, FastAPI, Pydantic v2, and SQLAlchemy async.
- **Database:** PostgreSQL with pgvector and AsyncPG.
- **Models:** Ollama local by default; Anthropic cloud is optional.

## Source Data

The included demo transcripts are synthetic examples, not real Lenny's Podcast content. Exact source mode can only quote material that has been indexed, and it cannot guarantee that the original source is correct. Use only transcript material you are authorized to process.


##Youtube Video
https://youtube.com/shorts/3PJy4l7VFTo?si=Fxcq8ZnEl-6bTx-L
