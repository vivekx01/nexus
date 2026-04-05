# Project Nexus

**Nexus** is an AI assistant built on [Deep Agents](https://github.com/langchain-ai/deepagents) and exposed through a small **FastAPI** backend. Nexus orchestrates specialized **LangGraph** subagents for tasks like research and social post generation, while keeping a single chat surface for clients.

## Features

- **Deep Agent runtime** — planning, tools, and delegation via the built-in `task` mechanism to compiled subagents.
- **Subagents** — each lives under `app/subagents/<name>/` with its own graph, state, nodes, and prompts.
- **Threaded chat** — optional `thread_id` on `/chat` so conversation state can persist per thread (checkpointer).
- **Time tool** — `get_current_datetime` fetches UTC time from public time APIs (not local clock) when recency matters.

## Requirements

- Python **3.12+**
- [uv](https://docs.astral.sh/uv/) (recommended) or pip
- An **OpenAI API key** for `ChatOpenAI`

## Quick start

### 1. Clone and install

```bash
cd "Project Nexus"
uv sync
```

### 2. Environment

Create a `.env` file in the project root (never commit real secrets):

```env
OPENAI_API_KEY=sk-...
USER_AGENT=ProjectNexus/1.0 (dev)
```

- **`OPENAI_API_KEY`** — required for the model.
- **`USER_AGENT`** — recommended when using DuckDuckGo-based search in the researcher tools; reduces noisy warnings and identifies outbound HTTP traffic responsibly.

### 3. Run the API

```bash
uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Open [http://127.0.0.1:8000/docs](http://127.0.0.1:8000/docs) for interactive OpenAPI docs.

### VS Code

Use **Run and Debug** (F5) with `.vscode/launch.json` — **Backend: FastAPI (uvicorn)** — to start the server with reload and `.env` loaded.

## API

| Method | Path | Description |
|--------|------|-------------|
| `POST` | `/chat` | Send a message to Nexus. Body: `{ "message": "...", "thread_id": "<optional uuid>" }`. Returns `response` and `thread_id`. |
| `GET` | `/health` | Liveness check and Deep Agents version. |
| `GET` | `/` | Short API info. |

All other behavior (research, social posts, etc.) is driven through **chat**: Nexus decides when to call tools or delegate to subagents.

## Architecture (high level)

```
app/
  main.py                 # FastAPI app, CORS, /chat route
  deep_agent_runtime.py   # Nexus: model, system prompt, tools, subagents, run_chat()
  subagents/
    social_media_agent/   # LangGraph: summarize → LinkedIn + Twitter → formatted messages
    researcher_agent/     # Research + web tools (see package for details)
```

- **Persona and rules** for Nexus live in `SYSTEM_PROMPT` inside `app/deep_agent_runtime.py`. Adjust name, tone, or ownership there if you fork the project.
- **Subagents** are registered as `CompiledSubAgent` instances and invoked by the main agent through delegation (`task`), not separate HTTP routes.

## Subagents (current)

| Subagent name | Role |
|---------------|------|
| `social_media_generator` | Summarizes article content and produces LinkedIn and Twitter-style output in parallel. |
| *(researcher)* | See `app/subagents/researcher_agent/` — search and scrape tooling wired for the researcher subagent. |

## Development

```bash
# Syntax check
python -m compileall app

# Lint (if you configure ruff/mypy locally)
# uv run ruff check app
```

## License

Add a license file if you distribute this repository.
