# The Lenny Growth Assistant

A local-first, source-grounded product and growth chat workbench. Its default Exact source mode returns a verbatim relevant transcript sentence with citation and does not call an LLM. Optional AI Answer, essay, and artifact modes use Ollama with Anthropic fallback. HTML artifacts use a sandboxed preview.

The bundled transcript samples are explicitly synthetic and are not Lenny's Podcast material. Ingest only sources you are authorized to use.

Exact source mode can only quote material that exists in the indexed transcript library and contains a relevant sentence. It cannot guarantee that source material itself is correct or answer questions absent from those sources. AI Answer, essay, and artifact modes are generated and may make mistakes.

## Quickstart

Prerequisites: Docker Desktop with Compose v2, and enough memory/storage for PostgreSQL and the selected Ollama model. First startup downloads the model and can take several minutes. Defaults are provided; copy `.env.example` to `.env` only when you want to customize them.

```sh
docker compose up --build
```

Open the UI at <http://localhost:3000>, API docs at <http://localhost:8000/docs>, and health at <http://localhost:8000/health>. Compose seeds the synthetic demo transcripts after the database is available. Stop with `Ctrl+C`; use `docker compose down` to stop/remove containers while preserving named volumes. `docker compose down -v` also deletes local conversation and model data.

## Configuration

### Ollama local (default)

Compose starts Ollama and pulls `OLLAMA_MODEL` (default `llama3.2`). Local inference is the default and does not need an API key. Change `OLLAMA_MODEL` in `.env` to another Ollama model supported by your machine; recreate the services with `docker compose up --build`.

For an Ollama instance running on the host instead, run PostgreSQL and the API manually or set `OLLAMA_BASE_URL` to a host-reachable address. Inside Compose, `localhost` refers to the container, so the configured service URL is `http://ollama:11434`.

### Anthropic cloud

Set `ANTHROPIC_API_KEY` in the ignored `.env` file and optionally set `DEFAULT_MODEL=anthropic`. The other provider remains the fallback. Never commit real keys. The configured model defaults to `claude-3-5-sonnet-20241022`.

### Authorized transcript ingestion

Send JSON records to `POST /api/ingest`:

```sh
curl -X POST http://localhost:8000/api/ingest \
  -H 'Content-Type: application/json' \
  -d '{"transcripts":[{"title":"Authorized interview","speaker":"Guest","timestamp":"00:12:34","url":"https://example.com/source","content":"Paste authorized transcript text here."}]}'
```

Fields `speaker`, `timestamp`, and `url` are optional. The ingestion endpoint accepts 1-100 records per request. Re-ingesting the same title and URL replaces its chunks.

## Manual Development

Frontend (Node.js 22+):

```sh
npm ci
npm run dev
npm run build
npm run lint
```

Backend (Python 3.11): create and activate a virtual environment, then from the repository root:

```sh
python -m venv .venv
# Windows: .venv\Scripts\activate
# macOS/Linux: source .venv/bin/activate
pip install -r backend/requirements.txt
```

Provide a PostgreSQL 16 database with pgvector, set `DATABASE_URL` and `OLLAMA_BASE_URL` (defaults are suitable for local services), then run:

```sh
cd backend
python -m app.ingest_cli
uvicorn app.main:app --reload
```

For local Ollama, install/start Ollama, pull the chosen model (`ollama pull llama3.2`), and set `OLLAMA_BASE_URL=http://localhost:11434`. For Anthropic fallback, set `ANTHROPIC_API_KEY` in the environment.

## Tests

With backend dependencies installed, from the repository root:

```sh
python -m pytest -q
```

Tests use in-memory SQLite and mocked providers; they do not require a running model or PostgreSQL server. Frontend checks are `npm run build` and `npm run lint`. To run backend tests in the Compose image after startup: `docker compose exec backend pytest -q /app/tests`.

## Manual UI Checklist

- Open a fresh session, ask a starter question, and confirm streamed text and source citations appear.
- Test Exact source mode with an indexed passage and confirm its wording and source citation match exactly; test an unrelated question and confirm it abstains.
- Switch between local/cloud providers and AI Answer/essay/artifact modes; confirm selected mode affects the request and generated artifacts open beside chat.
- Select a prior session and confirm its persisted messages and citations load.
- Stop Ollama with no cloud key and confirm the UI shows a retryable provider error rather than a fabricated response.
- Preview hostile HTML containing scripts, event handlers, `javascript:` links, and embedded frames; confirm these do not execute and do not affect the parent page.
- Test at mobile width, keyboard-only navigation, visible focus, and browser zoom.
- Check `/health` while PostgreSQL or a model provider is unavailable and verify component status is reported.

## Troubleshooting

- **Model pull is slow/fails:** Check disk, network, and available memory; inspect `docker compose logs ollama ollama-init`. The first model download is the largest cold-start cost.
- **API waits for startup:** The backend waits for PostgreSQL health and successful model pull. Inspect `docker compose ps` and the `ollama-init` logs.
- **Database extension error:** Use the included `pgvector/pgvector:pg16` image and inspect `docker compose logs postgres backend`.
- **UI says API offline:** Verify ports 3000 and 8000 are free and check `CORS_ORIGINS` / `VITE_API_URL` if using non-default ports or a remote host.
- **No citations:** The demo corpus is small. Ingest authorized transcript text and ask a query that matches its content; the app intentionally does not scrape sources.
- **Reset local data:** `docker compose down -v` deletes PostgreSQL conversations, indexed chunks, and downloaded Ollama models.

## Project Documents

- [Product requirements](PRD.md)
- [Architecture](architecture.md)
- [Design and security](design.md)
- [Illustrative agent traces](agent_transcripts/sample-execution.md)

## Deployment Note

This is a local, single-tenant demo foundation, not a public production deployment. Before exposing it to users, add authentication/authorization, request/rate limits, TLS, managed secrets, privacy-aware logging, backups, monitoring, and a stronger evaluated semantic embedding model. Source citations are pointers to retrieved evidence, not a guarantee of correctness.
