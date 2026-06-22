# all-pdfs-chat

Upload a PDF, let it be processed, then **ask questions about its contents** and get answers
grounded in the document — with the page numbers used as citations.

The answering layer is a **tool-calling agent**, not a fixed retrieval chain. That choice is
deliberate and central to where this project is going; see [Why an agent](#why-an-agent).

---

## What it does

```
upload PDF  →  classify pages  →  extract text  →  chat (grounded answers + citations)
```

1. **Upload** — `POST /api/v1/pdfs` stores the file and returns `201` immediately
   (`processing_status = uploaded`). No blocking.
2. **Process (background worker)** — classifies each page, then extracts its text with PyMuPDF
   (complex/scanned pages can optionally use Azure Document Intelligence).
   Status walks `uploaded → classifying → classified → parsing → parsed`.
3. **Chat** — once `parsed`, `POST /api/v1/pdfs/{id}/chat` answers questions about that PDF,
   grounded only in its extracted page text, returning `{answer, citations}`.

Everything is per-user and owner-scoped behind bearer-token auth.

---

## The agent

The chat layer is a hand-built [LangGraph](https://langchain-ai.github.io/langgraph/)
`StateGraph` that runs an **iterative model ↔ tools loop** over a single PDF's parsed text. It
runs on a **local [Ollama](https://ollama.com/) model** (free at inference, must support tool
calling) behind a swappable factory, and persists multi-turn memory in Postgres
(`thread_id = pdf_id`).

The model decides which tool to call, with what query, and when it has enough evidence to answer
or to say the document doesn't contain it. A step guard bounds the loop so it always terminates.

### Why an agent

Real questions rarely resolve in one retrieval hop. Answering usually means:

> search a topic → inspect results → reformulate → search again → read a full page →
> decide there's enough evidence → answer (or admit it isn't there).

That **iterative loop** — the model choosing *when* to retrieve, *which* tool, with *what* query,
and *when to stop* — is what earns an agent.

The loop also keeps retrieval **extensible**: each new tool simply drops in. Planned:

- **Semantic / vector search** — embeddings for meaning-based recall, not just keyword overlap.
- **[PageIndex](https://github.com/VectifyAI/PageIndex)** — structure-aware navigation of long docs.
- **Knowledge-graph search** — entity/relationship queries across the document.

---

## Architecture

A clean **hexagonal** split — delivery and infrastructure depend on application **ports**, never
the reverse.

- **Backend** (`backend/`) — Python 3.14, async FastAPI, `uv`. Five persistence ports
  (PDF, jobs, users, sessions, file storage) each with SQL + in-memory implementations.
  Upload (API) and processing (worker) are **separate processes**. The agent is reached only
  through a `ChatService` port.
- **Frontend** (`frontend/`) — Next.js App Router (React 19): upload, status polling, and a chat
  panel that unlocks at `parsed`.
- **Persistence** — PostgreSQL via SQLAlchemy + Alembic migrations; PDF bytes on local disk.

Detailed docs: **[`backend/backend.md`](backend/backend.md)** (layers, pipeline, endpoints,
config) and **[`frontend/README.md`](frontend/README.md)**.

---

## Run locally

```bash
# starts Postgres, syncs deps, runs migrations, launches API + worker + frontend
./scripts/dev.sh
```

For the agent you also need an Ollama model with tool-calling support:

```bash
ollama pull llama3.1   # served at OLLAMA_BASE_URL (default http://localhost:11434)
```

- App: http://localhost:3000 · API docs: http://127.0.0.1:8000/docs
- The **worker must run** or status stays at `uploaded`.

See [`backend/backend.md`](backend/backend.md) for manual setup, configuration, and the full
endpoint and status reference.
