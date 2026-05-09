# DocIntel

Industrial Document Analysis Framework — ingest, chunk, embed, and query technical documents with one import.

DocIntel is a RAG (Retrieval-Augmented Generation) toolkit for engineers and developers who need to ask questions over large sets of technical documents such as maintenance manuals, schematics, safety procedures, and log files. It supports multiple LLM providers, a PostgreSQL vector backend, an HTTP API server, structured logging, and optional knowledge-graph retrieval.

```python
import os
import docintel as di

di.configure(gemini_api_key=os.environ["GEMINI_API_KEY"])
di.ingest("maintenance_manual.pdf")

result = di.ask("What is the maximum operating pressure?")
print(result.answer)
# → "The maximum operating pressure is 10 bar [Source 1, page 4]."

for source in result.sources:
    print(source.score, source.chunk.metadata.get("page"), source.chunk.text[:120])
```

---

## Table of Contents

1. [Features](#features)
2. [Requirements](#requirements)
3. [Installation](#installation)
4. [Quickstart](#quickstart)
5. [Python API Reference](#python-api-reference)
6. [Configuration Reference](#configuration-reference)
7. [HTTP Server](#http-server)
8. [LLM Providers](#llm-providers)
9. [Storage Backends](#storage-backends)
10. [RAG Modes](#rag-modes)
11. [Source Citations](#source-citations)
12. [Multi-Tenancy](#multi-tenancy)
13. [Security](#security)
14. [Structured Logging](#structured-logging)
15. [Metrics](#metrics)
16. [Supported File Types](#supported-file-types)
17. [Architecture](#architecture)
18. [Development](#development)
19. [License](#license)

---

## Features

- **One-import API** — `configure`, `ingest`, `ingest_dir`, `ask`, `search`, `delete`, `stats`
- **Class-based Pipeline** for explicit multi-tenant and multi-pipeline setups
- **Multi-provider LLM support** — Google Gemini, OpenAI, Anthropic Claude, and local Ollama
- **PDF page citations** — answers include `[Source N, page P]` markers grounded in the actual document
- **Hierarchical chunking** — heading-aware with breadcrumb metadata for rich, navigable retrieval
- **Contextual Retrieval** — optional document-level summarization prepended to each chunk before embedding
- **In-memory vector store** with atomic JSON persistence for local and prototype use
- **PostgreSQL + pgvector** backend for production-grade persistent vector search
- **FastAPI HTTP server** with OpenAPI/Swagger UI, API key authentication, per-IP rate limiting, and path traversal protection
- **LightRAG integration** for knowledge-graph-based retrieval (graph and hybrid modes)
- **Structured JSON logging** with per-request correlation IDs and stage timings
- **Thread-safe metrics** — counters for documents, chunks, queries, API calls, and retries
- **Multi-tenancy** — every operation accepts a `tenant_id` to partition data into isolated namespaces
- **64 tests** covering unit, integration, and security scenarios; no API key required for the test suite

---

## Requirements

- Python 3.10+
- At least one LLM provider API key (Gemini, OpenAI, or Anthropic), or a running Ollama instance
- PostgreSQL 14+ with the `pgvector` extension (only if using `vector_store="pgvector"`)
- `uv` recommended for local development

---

## Installation

### From Source (Recommended for Development)

```bash
git clone https://github.com/your-org/docintel.git
cd docintel
uv sync --extra dev
```

### Install Extras

Install only what you need:

```bash
# HTTP server (FastAPI + uvicorn)
uv sync --extra server

# OpenAI provider
uv sync --extra openai

# Anthropic provider
uv sync --extra anthropic

# PostgreSQL backend
uv sync --extra postgres

# LightRAG graph retrieval
uv sync --extra graph

# All extras at once
uv sync --extra dev --extra server --extra openai --extra anthropic --extra postgres --extra graph
```

### Windows Note

If your shell resolves to the Windows Store Python shim, pin uv explicitly:

```powershell
$env:UV_CACHE_DIR = ".uv-cache"
$env:UV_PYTHON_INSTALL_DIR = ".uv-python"
uv sync --python 3.12 --extra dev
```

---

## Quickstart

### Gemini (default)

```python
import os
import docintel as di

di.configure(gemini_api_key=os.environ["GEMINI_API_KEY"])

di.ingest("safety_manual.pdf")
result = di.ask("What are the lockout-tagout steps?")
print(result.answer)
```

### OpenAI

```python
from docintel import Pipeline

p = Pipeline(
    provider="openai",
    openai_api_key=os.environ["OPENAI_API_KEY"],
)
p.ingest("hydraulic_manual.pdf")
result = p.ask("What is the pump pressure limit?")
print(result.answer)
```

### Anthropic Claude (generation) + OpenAI (embeddings)

```python
from docintel import Pipeline

p = Pipeline(
    provider="anthropic",
    anthropic_api_key=os.environ["ANTHROPIC_API_KEY"],
    embedding_provider="openai",
    openai_api_key=os.environ["OPENAI_API_KEY"],
)
p.ingest("maintenance_procedure.pdf")
result = p.ask("What are the preventive maintenance intervals?")
print(result.answer)
```

### Local Ollama (no API key required)

```python
from docintel import Pipeline

# Requires: ollama serve (running locally with llama3.2 + nomic-embed-text pulled)
p = Pipeline(provider="ollama", ollama_base_url="http://localhost:11434")
p.ingest("sop.pdf")
result = p.ask("What PPE is required?")
print(result.answer)
```

### Batch Ingestion

```python
from docintel import Pipeline

p = Pipeline(
    gemini_api_key=os.environ["GEMINI_API_KEY"],
    persist_dir=".docintel",
)

docs = p.ingest_dir("manuals/", tenant_id="plant_a", recursive=True)
print(f"Indexed {len(docs)} documents, {p.stats()['total_chunks']} chunks")
```

### Search Without Generation

```python
hits = di.search("hydraulic pump cavitation", tenant_id="plant_a", top_k=5)

for hit in hits:
    print(f"{hit.score:.3f} | page {hit.chunk.metadata.get('page')} | {hit.chunk.text[:200]}")
```

---

## Python API Reference

### Module-Level API (`import docintel as di`)

The module-level API uses an internal singleton pipeline, suitable for single-pipeline scripts.

---

#### `di.configure(...) → Pipeline`

Initialize the default pipeline. Call this once before using any other module-level function.

| Parameter | Type | Default | Description |
|---|---|---|---|
| `gemini_api_key` | `str` | — | Gemini API key (required when `provider="gemini"`) |
| `provider` | `str` | `"gemini"` | LLM provider: `"gemini"`, `"openai"`, `"anthropic"`, `"ollama"` |
| `embedding_provider` | `str \| None` | `None` | Override embedding provider (required for Anthropic) |
| `openai_api_key` | `str \| None` | `None` | OpenAI API key |
| `anthropic_api_key` | `str \| None` | `None` | Anthropic API key |
| `ollama_base_url` | `str` | `"http://localhost:11434"` | Ollama server URL |
| `generation_model` | `str \| None` | provider default | Model for answers and summaries |
| `embedding_model` | `str \| None` | provider default | Model for embeddings |
| `chunk_size` | `int` | `600` | Approximate words per chunk |
| `chunk_overlap` | `int` | `80` | Word overlap between adjacent chunks |
| `min_chunk_size` | `int` | `80` | Chunks smaller than this are discarded |
| `top_k` | `int` | `5` | Default retrieval count per query |
| `vector_store` | `str` | `"memory"` | Storage backend: `"memory"` or `"pgvector"` |
| `persist_dir` | `str \| None` | `".docintel"` | Directory for JSON persistence (memory store) |
| `db_url` | `str \| None` | `None` | PostgreSQL DSN (required for `pgvector`) |
| `embed_batch_size` | `int` | `20` | Texts per embedding API call |
| `max_retries` | `int` | `5` | Retry attempts for API calls |

> **Note:** `di.configure()` only accepts `gemini_api_key` directly. For other providers, use `Pipeline(provider=..., ...)` directly.

---

#### `di.ingest(path, ...) → Document`

Extract, chunk, embed, and store a document.

```python
doc = di.ingest(
    path="manual.pdf",
    tenant_id="default",   # logical namespace
    summarize=True,        # prepend document summary to each chunk for Contextual Retrieval
    verbose=True,          # log each stage to stdout
)
```

**Returns** a `Document` with:
- `id` — UUID
- `path` — resolved absolute path
- `tenant_id`
- `summary` — LLM-generated summary (if `summarize=True`)
- `chunks` — list of `Chunk` objects
- `metadata` — `{"file_name", "file_suffix", "file_size", "sha256"}`

---

#### `di.ingest_dir(path, ...) → list[Document]`

Ingest all supported files in a directory.

```python
docs = di.ingest_dir(
    path="manuals/",
    tenant_id="plant_a",
    recursive=True,    # descend into subdirectories
    summarize=True,
    verbose=True,
)
```

Files are processed in sorted path order. Unsupported extensions are skipped silently.

---

#### `di.ask(question, ...) → QueryResult`

Retrieve relevant chunks, then generate a grounded answer with inline source citations.

```python
result = di.ask(
    question="What is the shutdown procedure?",
    tenant_id="default",
    top_k=None,    # uses config default (5) if None
)

print(result.answer)      # "Step 1: ... [Source 1, page 12]. Step 2: ... [Source 2, page 14]."
print(result.sources)     # list[SearchResult]
print(result.model)       # "gemini-2.5-flash"
```

If no documents are indexed, the answer is `"No relevant documents found. Please ingest documents first."`.

---

#### `di.search(query, ...) → list[SearchResult]`

Semantic similarity search. Returns ranked chunks without generating an answer.

```python
hits = di.search(query="pump pressure", tenant_id="default", top_k=5)

for hit in hits:
    print(hit.score)           # cosine similarity (0.0–1.0)
    print(hit.document_path)   # absolute path to source file
    print(hit.tenant_id)
    print(hit.chunk.text)
    print(hit.chunk.metadata)  # {"page", "breadcrumb", "doc_summary", ...}
```

---

#### `di.delete(path, tenant_id="default") → None`

Remove all chunks for a specific document from the index.

```python
di.delete("old_manual.pdf", tenant_id="plant_a")
```

---

#### `di.stats() → dict`

Return store statistics.

```python
di.stats()
# {"total_chunks": 1842, "tenants": ["plant_a", "plant_b"]}
```

---

### Class-Based API (`Pipeline`)

For multi-tenant setups, multiple independent pipelines, or when you need explicit control.

```python
from docintel import Pipeline, Config

# Minimal construction
p = Pipeline(gemini_api_key="YOUR_KEY")

# Explicit Config object
config = Config(
    provider="openai",
    openai_api_key="YOUR_KEY",
    vector_store="pgvector",
    db_url="postgresql://user:pass@localhost:5432/docintel",
    chunk_size=400,
    top_k=8,
)
p = Pipeline(config)
```

`Pipeline` exposes the same methods as the module-level API: `ingest`, `ingest_dir`, `ask`, `search`, `delete`, `stats`.

---

## Configuration Reference

| Field | Type | Default | Description |
|---|---|---|---|
| `provider` | `str` | `"gemini"` | LLM provider |
| `embedding_provider` | `str \| None` | `None` | Companion embedding provider (required for Anthropic) |
| `gemini_api_key` | `str \| None` | — | Required when `provider="gemini"` |
| `openai_api_key` | `str \| None` | — | Required when `provider="openai"` or `embedding_provider="openai"` |
| `anthropic_api_key` | `str \| None` | — | Required when `provider="anthropic"` |
| `ollama_base_url` | `str` | `"http://localhost:11434"` | Ollama server base URL |
| `generation_model` | `str \| None` | provider default | Model for generation and summarization |
| `embedding_model` | `str \| None` | provider default | Model for embeddings |
| `summarization_model` | `str \| None` | `generation_model` | Reserved override for summarization model |
| `chunk_size` | `int` | `600` | Approximate words per chunk |
| `chunk_overlap` | `int` | `80` | Word overlap between adjacent chunks |
| `min_chunk_size` | `int` | `80` | Minimum chunk size (smaller chunks discarded) |
| `top_k` | `int` | `5` | Default retrieval count per query |
| `vector_store` | `str` | `"memory"` | `"memory"` or `"pgvector"` |
| `db_url` | `str \| None` | — | PostgreSQL DSN (required for `pgvector`) |
| `persist_dir` | `str \| None` | `".docintel"` | JSON persistence directory (memory store) |
| `embedding_dim` | `int \| None` | provider default | Embedding vector size (auto-resolved) |
| `pg_pool_min` | `int` | `2` | Minimum PostgreSQL connections |
| `pg_pool_max` | `int` | `10` | Maximum PostgreSQL connections |
| `embed_batch_size` | `int` | `20` | Texts per embedding API call |
| `max_retries` | `int` | `5` | Maximum retry attempts for API calls |
| `rag_mode` | `str` | `"vector"` | Retrieval mode: `"vector"`, `"graph"`, `"hybrid"` |
| `lightrag_dir` | `str` | `".docintel_graph"` | LightRAG working directory |
| `api_key` | `str \| None` | `None` | Server API key (requires `X-API-Key` header) |
| `allowed_ingest_dirs` | `list[str]` | `[]` | Restrict `/ingest` to these paths (empty = allow all) |
| `rate_limit_rpm` | `int` | `0` | Per-IP rate limit in requests/minute (0 = disabled) |

**Provider model defaults:**

| Provider | Generation model | Embedding model | Embedding dim |
|---|---|---|---|
| `gemini` | `gemini-2.5-flash` | `gemini-embedding-001` | 3072 |
| `openai` | `gpt-4o` | `text-embedding-3-large` | 3072 |
| `anthropic` | `claude-opus-4-7` | _(delegates to embedding_provider)_ | — |
| `ollama` | `llama3.2` | `nomic-embed-text` | 768 |

Invalid configuration raises `ValueError` at startup with a descriptive message.

---

## HTTP Server

DocIntel ships with a FastAPI HTTP server that exposes all pipeline operations over REST. It includes OpenAPI/Swagger documentation, structured logging middleware, API key authentication, and per-IP rate limiting.

### Start the Server

**Gemini backend (simplest):**

```bash
python -m docintel.server \
  --provider gemini \
  --gemini-api-key YOUR_KEY \
  --port 8000
```

**OpenAI backend with PostgreSQL:**

```bash
python -m docintel.server \
  --provider openai \
  --openai-api-key YOUR_KEY \
  --backend pgvector \
  --backend-url "postgresql://user:pass@localhost:5432/docintel" \
  --port 8000
```

**Anthropic + OpenAI embeddings:**

```bash
python -m docintel.server \
  --provider anthropic \
  --anthropic-api-key YOUR_KEY \
  --embedding-provider openai \
  --openai-api-key YOUR_OPENAI_KEY \
  --port 8000
```

**With security:**

```bash
python -m docintel.server \
  --gemini-api-key YOUR_KEY \
  --api-key "my-secret-token" \
  --allowed-ingest-dirs /data/manuals /data/procedures \
  --rate-limit-rpm 60 \
  --port 8000
```

**All CLI flags:**

| Flag | Default | Description |
|---|---|---|
| `--host` | `0.0.0.0` | Bind address |
| `--port` | `8000` | Listen port |
| `--provider` | `gemini` | LLM provider |
| `--embedding-provider` | — | Companion embedding provider (for Anthropic) |
| `--gemini-api-key` | — | Gemini API key |
| `--openai-api-key` | — | OpenAI API key |
| `--anthropic-api-key` | — | Anthropic API key |
| `--ollama-base-url` | `http://localhost:11434` | Ollama URL |
| `--backend` | `memory` | Storage: `memory` or `pgvector` |
| `--backend-url` | — | PostgreSQL DSN (required for pgvector) |
| `--persist-dir` | `.docintel` | JSON persistence directory |
| `--rag-mode` | `vector` | Retrieval: `vector`, `graph`, `hybrid` |
| `--lightrag-dir` | `.docintel_graph` | LightRAG working directory |
| `--api-key` | — | Require `X-API-Key` on all routes except `/health` |
| `--allowed-ingest-dirs` | _(all)_ | Whitelist directories for `/ingest` |
| `--rate-limit-rpm` | `0` | Per-IP rate limit (0 = off) |
| `--log-level` | `INFO` | Log level |
| `--log-json` | enabled | Emit structured JSON logs |

### Interactive API Docs

Once the server is running, open:

- **Swagger UI:** `http://localhost:8000/docs`
- **ReDoc:** `http://localhost:8000/redoc`

### Endpoints

| Method | Path | Description |
|---|---|---|
| `GET` | `/health` | Health check (no auth required) |
| `POST` | `/ingest` | Ingest a document |
| `POST` | `/search` | Semantic search |
| `POST` | `/ask` | RAG question answering |
| `DELETE` | `/documents/{doc_id}` | Delete a document |
| `GET` | `/stats` | Store and metrics statistics |

---

### `GET /health`

No authentication required. Used for load-balancer health checks.

```bash
curl http://localhost:8000/health
```

```json
{
  "status": "ok",
  "store_backend": "pgvector",
  "metrics": {
    "docs_ingested": 12,
    "chunks_indexed": 3840,
    "queries": 47,
    "embed_api_calls": 195,
    "retries": 0,
    "uptime_seconds": 3600
  }
}
```

---

### `POST /ingest`

```bash
curl -X POST http://localhost:8000/ingest \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-token" \
  -d '{"path": "/data/manuals/pump_manual.pdf", "tenant_id": "plant_a"}'
```

**Request body:**

```json
{
  "path": "/absolute/path/to/document.pdf",
  "tenant_id": "default",
  "summarize": true
}
```

**Response:**

```json
{
  "id": "3fa85f64-5717-4562-b3fc-2c963f66afa6",
  "path": "/absolute/path/to/document.pdf",
  "tenant_id": "default",
  "summary": "This manual covers...",
  "metadata": {
    "file_name": "document.pdf",
    "file_suffix": ".pdf",
    "file_size": 204800,
    "sha256": "a1b2c3..."
  },
  "chunk_count": 148
}
```

> **Security note:** When `--allowed-ingest-dirs` is configured, paths outside those directories return HTTP 403. All paths are resolved with `os.path.realpath()` to prevent symlink-based traversal.

---

### `POST /search`

```bash
curl -X POST http://localhost:8000/search \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-token" \
  -d '{"query": "pump pressure limit", "tenant_id": "plant_a", "top_k": 5}'
```

**Request body:**

```json
{
  "query": "pump pressure limit",
  "tenant_id": "default",
  "top_k": 5
}
```

**Response:** Array of `SearchResult` objects with `chunk`, `score`, `document_path`, `tenant_id`.

---

### `POST /ask`

```bash
curl -X POST http://localhost:8000/ask \
  -H "Content-Type: application/json" \
  -H "X-API-Key: my-secret-token" \
  -d '{"question": "What is the maximum operating pressure?", "tenant_id": "plant_a"}'
```

**Request body:**

```json
{
  "question": "What is the maximum operating pressure?",
  "tenant_id": "default",
  "top_k": null
}
```

**Response:**

```json
{
  "question": "What is the maximum operating pressure?",
  "answer": "The maximum operating pressure is 10 bar [Source 1, page 4].",
  "sources": [...],
  "model": "gemini-2.5-flash"
}
```

---

### `DELETE /documents/{doc_id}`

```bash
curl -X DELETE "http://localhost:8000/documents/path%2Fto%2Fdoc.pdf?tenant_id=plant_a" \
  -H "X-API-Key: my-secret-token"
```

Returns HTTP 204 on success.

---

### `GET /stats`

```bash
curl http://localhost:8000/stats -H "X-API-Key: my-secret-token"
```

```json
{
  "total_chunks": 3840,
  "tenants": ["plant_a", "plant_b"],
  "store": null
}
```

---

## LLM Providers

### Google Gemini

Default provider. Requires a Gemini API key from [Google AI Studio](https://aistudio.google.com/).

```python
Pipeline(provider="gemini", gemini_api_key="YOUR_KEY")
```

- Generation: `gemini-2.5-flash` (default)
- Embeddings: `gemini-embedding-001` (3072-dim)
- Includes automatic retry with exponential backoff

### OpenAI

```bash
pip install 'docintel[openai]'
```

```python
Pipeline(provider="openai", openai_api_key="YOUR_KEY")
```

- Generation: `gpt-4o` (default)
- Embeddings: `text-embedding-3-large` (3072-dim)

### Anthropic Claude

Anthropic does not provide an embeddings API. You must specify a companion `embedding_provider`.

```bash
pip install 'docintel[anthropic,openai]'
```

```python
Pipeline(
    provider="anthropic",
    anthropic_api_key="YOUR_KEY",
    embedding_provider="openai",       # or "ollama"
    openai_api_key="YOUR_OPENAI_KEY",
)
```

- Generation: `claude-opus-4-7` (default)
- Embeddings: delegated to `embedding_provider`

### Ollama (Local, No API Key)

Run models locally with no network dependency or API cost.

```bash
# Install Ollama: https://ollama.com
ollama serve
ollama pull llama3.2
ollama pull nomic-embed-text
```

```python
Pipeline(provider="ollama", ollama_base_url="http://localhost:11434")
```

- Generation: `llama3.2` (default)
- Embeddings: `nomic-embed-text` (768-dim)
- Override any model name via `generation_model` and `embedding_model` fields

---

## Storage Backends

### In-Memory (default)

Vectors are held in process memory and saved to a versioned JSON file on every write. Suitable for local tools, development, and small document sets.

```python
Pipeline(gemini_api_key="KEY", vector_store="memory", persist_dir=".docintel")
```

Index is saved to `.docintel/docintel_index.json` using atomic file writes. It is loaded automatically on startup.

**Limitations:** not suitable for concurrent multi-process deployments, datasets larger than available RAM, or high-availability requirements.

### PostgreSQL + pgvector

Production-grade persistent vector search. Requires PostgreSQL 14+ with the `pgvector` extension.

```bash
pip install 'docintel[postgres]'
```

```python
Pipeline(
    gemini_api_key="KEY",
    vector_store="pgvector",
    db_url="postgresql://user:pass@localhost:5432/docintel",
)
```

The schema is auto-migrated on first connect (idempotent DDL). The store uses `HNSW` indexing for approximate nearest-neighbor search and a `ThreadedConnectionPool` for concurrent access.

**Features:**
- Persistent across restarts
- Multi-process safe
- Tenant-partitioned queries
- `ON CONFLICT ... DO UPDATE` for duplicate chunk handling
- Connection pooling (2 min / 10 max by default)

---

## RAG Modes

DocIntel supports three retrieval strategies controlled by `rag_mode`.

### `"vector"` (default)

Standard vector similarity search. Fast, accurate for well-structured documents.

```python
Pipeline(gemini_api_key="KEY", rag_mode="vector")
```

### `"graph"` — LightRAG Knowledge Graph

Uses LightRAG to extract a knowledge graph from documents and answer questions using entity/relationship reasoning. Better for questions requiring multi-hop reasoning across many documents.

```bash
pip install 'docintel[graph]'
```

```python
Pipeline(
    gemini_api_key="KEY",
    rag_mode="graph",
    lightrag_dir=".docintel_graph",
)
```

Answers use LightRAG's internal hybrid retrieval. `sources` in the `QueryResult` is empty (no per-chunk citations in this mode).

### `"hybrid"` — LightRAG Answer + Vector Citations

Generates the answer using LightRAG's reasoning while also returning vector-based `sources` for citations and grounding.

```python
Pipeline(gemini_api_key="KEY", rag_mode="hybrid")
```

---

## Source Citations

In `"vector"` and `"hybrid"` RAG modes, the LLM is instructed to include inline source citations in its answer:

```
The maximum operating pressure is 10 bar [Source 1, page 4].
Emergency shutdown is described in section 3.2 [Source 2, page 18].
```

Citations follow the format `[Source N]` or `[Source N, page P]` where the page number is drawn from the document's actual page metadata. For text files, the page number is a 1-indexed paragraph segment number.

The `sources` list in `QueryResult` and `/ask` responses maps `Source N` to its actual chunk, document path, page, and similarity score.

---

## Multi-Tenancy

Every indexing, search, and query operation accepts a `tenant_id`. Data is partitioned by tenant so one tenant's documents never appear in another tenant's results.

```python
# Ingest into separate tenants
di.ingest("plant_a_manual.pdf", tenant_id="plant_a")
di.ingest("plant_b_manual.pdf", tenant_id="plant_b")

# Results are isolated
di.ask("What is the pressure limit?", tenant_id="plant_a")
di.ask("What is the pressure limit?", tenant_id="plant_b")

# Delete only from one tenant
di.delete("plant_a_manual.pdf", tenant_id="plant_a")
```

**Memory store:** tenant isolation is logical — all chunks share one JSON file, partitioned by `tenant_id` key. This is not a security boundary; it prevents cross-tenant results within the library.

**pgvector:** tenant isolation is enforced at the SQL level with a `tenant_id TEXT NOT NULL` column and filtered queries.

---

## Security

DocIntel's HTTP server includes three security features:

### API Key Authentication

When `--api-key` is set, every request (except `GET /health`) must include the header:

```
X-API-Key: your-secret-token
```

Comparison uses `hmac.compare_digest` to prevent timing attacks. Missing or incorrect keys return HTTP 403.

```bash
python -m docintel.server --gemini-api-key KEY --api-key "my-secret-token"
```

### Path Traversal Prevention

When `--allowed-ingest-dirs` is set, the `/ingest` endpoint rejects any path that is not inside one of the configured directories. All paths are resolved with `os.path.realpath()` before comparison, which resolves symlinks and prevents traversal via `../` sequences.

```bash
python -m docintel.server \
  --gemini-api-key KEY \
  --allowed-ingest-dirs /data/manuals /data/procedures
```

Requests to paths outside these directories return HTTP 403.

### Per-IP Rate Limiting

When `--rate-limit-rpm` is set to a positive integer, requests from a single client IP are limited to that many requests per minute using a sliding-window counter. Requests exceeding the limit return HTTP 429 with a `Retry-After` header.

```bash
python -m docintel.server --gemini-api-key KEY --rate-limit-rpm 60
```

The `GET /health` endpoint is exempt from rate limiting to allow load-balancer checks.

---

## Structured Logging

DocIntel emits structured JSON logs from the pipeline and server. Each log entry includes a `correlation_id` for end-to-end request tracing, stage timings in milliseconds, and context fields such as `tenant_id`, `path`, and `chunks`.

```bash
python -m docintel.server --gemini-api-key KEY --log-level INFO
```

Example log line (formatted for readability):

```json
{
  "time": "2026-05-09T12:00:01.234Z",
  "level": "INFO",
  "logger": "docintel._pipeline",
  "msg": "ingest_done",
  "correlation_id": "3fa85f64-5717-4562-b3fc",
  "path": "/data/manuals/pump.pdf",
  "tenant": "plant_a",
  "chunks": 148,
  "ms": 4120
}
```

Every HTTP request automatically receives a `correlation_id` from the `X-Correlation-Id` request header (or a newly generated UUID if absent). The same ID is returned in the `X-Correlation-Id` response header and in all logs for that request.

**Enable from Python:**

```python
from docintel import configure_logging
configure_logging(level="INFO", json_format=True)
```

---

## Metrics

DocIntel tracks runtime metrics using a thread-safe in-process counter.

```python
from docintel import get_metrics
print(get_metrics())
```

```json
{
  "docs_ingested": 12,
  "chunks_indexed": 3840,
  "queries": 47,
  "embed_api_calls": 195,
  "retries": 0,
  "uptime_seconds": 3600
}
```

Metrics are also returned by `GET /health` and `GET /stats`. The counters reset on server restart. A Prometheus adapter can wrap `get_metrics()` without changes to the core counters.

---

## Supported File Types

| Extension | Extractor | Notes |
|---|---|---|
| `.pdf` | `PdfExtractor` | Text-based PDFs. Page numbers are 1-indexed PDF page numbers. |
| `.txt` | `TextExtractor` | Split by blank lines. Segment number used as page. |
| `.md` | `TextExtractor` | Markdown. |
| `.rst` | `TextExtractor` | reStructuredText. |
| `.log` | `TextExtractor` | Log files. |

Scanned PDFs require OCR (not yet implemented). CAD/DXF extraction is on the roadmap.

---

## Architecture

```
Document file
      │
      ▼
  Extractor  ──── page-level text with page numbers
      │
      ▼
 Summarizer  ──── LLM-generated document summary (Contextual Retrieval)
      │
      ▼
HierarchicalChunker  ──── heading-aware chunks with breadcrumb metadata
      │
      ▼
   Embedder  ──── batched embedding API calls
      │
      ▼
 VectorStore  ──── memory (JSON) or pgvector (PostgreSQL)
                         │
         ┌───────────────┘
         │
Question ─► EmbedQuery ─► VectorSearch ─► BuildContext ─► LLM Answer
                                                │
                                                └── [Source N, page P] citations
```

**Optional LightRAG path (graph / hybrid mode):**

```
Document text ─► LightRAG.insert() ─► Knowledge Graph (entities + relations)
                                              │
Question ──────────────────────────► LightRAG.query() ─► Graph-grounded answer
```

**Key modules:**

| Module | Responsibility |
|---|---|
| `docintel/_pipeline.py` | Orchestrates ingest, search, ask, delete |
| `docintel/_config.py` | Dataclass config with validation |
| `docintel/core/entities.py` | `Document`, `Chunk`, `SearchResult`, `QueryResult` |
| `docintel/extractors/` | PDF and text file extraction |
| `docintel/processing/chunker.py` | Hierarchical heading-aware chunking |
| `docintel/processing/embedder.py` | Batched embedding |
| `docintel/llm/base.py` | `BaseLLMClient` ABC |
| `docintel/llm/gemini.py` | Gemini client with retry |
| `docintel/llm/openai_client.py` | OpenAI client |
| `docintel/llm/anthropic_client.py` | Anthropic client (generation only) |
| `docintel/llm/ollama_client.py` | Ollama local client |
| `docintel/storage/memory.py` | In-memory + JSON persistence |
| `docintel/storage/pgvector.py` | PostgreSQL + pgvector |
| `docintel/lightrag_index.py` | LightRAG knowledge graph wrapper |
| `docintel/logging.py` | Structured JSON logging + correlation IDs |
| `docintel/metrics.py` | Thread-safe counters |
| `docintel/server/app.py` | FastAPI app factory with lifespan |
| `docintel/server/routes.py` | HTTP endpoint handlers |
| `docintel/server/middleware.py` | Auth, rate limiting, correlation ID |
| `docintel/server/schemas.py` | Pydantic request/response models |

---

## Development

### Run Tests

```bash
uv run pytest
```

The test suite uses deterministic fake LLM/embedding clients. No API key or network access is required. Currently: **64 tests pass, 6 skipped** (pgvector integration tests require a PostgreSQL instance).

**Run pgvector integration tests:**

```bash
$env:DOCINTEL_TEST_PG_URL = "postgresql://user:pass@localhost:5432/docintel_test"
uv run pytest -m integration
```

### Lint

```bash
uv run ruff check .
```

### Build

```bash
uv build --python 3.12
```

### Project Layout

```
docintel/
├── __init__.py              # Module-level singleton API
├── _config.py               # Config dataclass with validation
├── _pipeline.py             # Central orchestrator
├── logging.py               # Structured JSON logging
├── metrics.py               # Thread-safe metrics counters
├── lightrag_index.py        # LightRAG knowledge graph wrapper
├── core/
│   └── entities.py          # Document, Chunk, SearchResult, QueryResult
├── extractors/
│   ├── pdf.py               # PDF extraction (pypdf)
│   └── text.py              # Plain-text extraction
├── processing/
│   ├── chunker.py           # Hierarchical heading-aware chunker
│   └── embedder.py          # Batched embedding
├── llm/
│   ├── base.py              # BaseLLMClient ABC
│   ├── gemini.py            # Google Gemini
│   ├── openai_client.py     # OpenAI
│   ├── anthropic_client.py  # Anthropic Claude
│   └── ollama_client.py     # Local Ollama
├── storage/
│   ├── base.py              # VectorStore ABC
│   ├── memory.py            # In-memory + JSON persistence
│   ├── pgvector.py          # PostgreSQL + pgvector
│   └── migrations/
│       └── 001_init.sql     # PostgreSQL schema (auto-applied)
└── server/
    ├── __main__.py          # CLI entry point
    ├── app.py               # FastAPI app factory
    ├── routes.py            # HTTP endpoints
    ├── schemas.py           # Pydantic models
    └── middleware.py        # Auth, rate limiting, correlation IDs
```

---

## License

MIT — see [LICENSE](LICENSE).
