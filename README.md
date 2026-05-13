# DocIntel

**Enterprise document intelligence platform — ingest, search, and query your documents with AI.**

DocIntel is a self-hosted RAG (Retrieval-Augmented Generation) platform for organizations that need to extract knowledge from large document collections. It combines a FastAPI backend, PostgreSQL + pgvector for vector storage, a Next.js web interface, multi-tenant access control, and pluggable LLM providers into a single deployable stack.

```python
import docintel as di

di.configure(gemini_api_key="...")
di.ingest("maintenance_manual.pdf")

result = di.ask("What is the maximum operating pressure?")
# → "The maximum operating pressure is 10 bar [Source 1, page 4]."
```

---

## Table of Contents

- [Features](#features)
- [Architecture](#architecture)
- [Quick Start — Docker Compose](#quick-start--docker-compose)
- [Manual Setup](#manual-setup)
- [Configuration](#configuration)
- [LLM Providers](#llm-providers)
- [OCR Support](#ocr-support)
- [Pipeline Modes](#pipeline-modes)
- [Python Library API](#python-library-api)
- [HTTP Server](#http-server)
- [Roles and Permissions](#roles-and-permissions)
- [Knowledge Graph](#knowledge-graph)
- [Documentation](#documentation)

---

## Features

| Category | Capability |
|---|---|
| **Ingestion** | PDF, Word, Excel, PowerPoint, CSV, Markdown, HTML, plain text |
| **OCR** | Scanned PDFs and image files (PNG, JPG, TIFF, BMP, WebP) via Tesseract |
| **LLM Providers** | Google Gemini, OpenAI, Anthropic Claude, NVIDIA NIM, Ollama (local) |
| **Retrieval** | Semantic vector search (pgvector cosine), optional knowledge graph (LightRAG) |
| **Pipeline Modes** | Single LLM answer, or Writer + Reviewer (two sequential calls for higher accuracy) |
| **Multi-tenancy** | Per-organisation data isolation, collection namespaces |
| **Auth** | JWT access tokens (1 h) + refresh tokens (7 d), bcrypt passwords, invite flow |
| **API Key Vault** | Per-provider encrypted key storage (Fernet AES-128) |
| **Frontend** | Next.js 14 web app — Ask AI, Documents, Search, Knowledge Graph, History, Admin |
| **Storage** | In-memory JSON (dev) or PostgreSQL 16 + pgvector (production) |
| **Observability** | Structured JSON logs, correlation IDs, per-org metrics |
| **Security** | CORS, per-IP rate limiting, path-traversal protection, bcrypt-12 |

---

## Architecture

```
┌─────────────────────────────────────────────────────────────────────┐
│  Browser / Client                                                   │
│  Next.js 14 (port 3000)                                             │
│  Ask AI · Documents · Search · Graph · History · Admin              │
└───────────────────────────────┬─────────────────────────────────────┘
                                │ HTTP / REST
                                ▼
┌─────────────────────────────────────────────────────────────────────┐
│  FastAPI Backend (port 8000)                                        │
│                                                                     │
│  ┌─────────────┐  ┌──────────────┐  ┌──────────────────────────┐  │
│  │ Auth Routes │  │  Doc Routes  │  │ Admin / Superadmin Routes│  │
│  │  /auth/*    │  │  /upload     │  │  /admin/*  /superadmin/* │  │
│  │  JWT + bcrypt│  │  /ask /search│  │  Org mgmt, settings, keys│  │
│  └─────────────┘  └──────────────┘  └──────────────────────────┘  │
│                                                                     │
│  ┌──────────────────────────────────────────────────────────────┐  │
│  │  Pipeline Registry (per-org Pipeline instance cache)         │  │
│  │                                                              │  │
│  │  Extractor → Chunker → Embedder → VectorStore                │  │
│  │  PDF / DOCX / XLSX / PPTX / HTML / CSV / TXT / Images (OCR) │  │
│  └──────────────────────────────────────────────────────────────┘  │
│                                                                     │
│  ┌──────────────┐  ┌────────────────────────────────────────────┐  │
│  │  LLM Client  │  │  LightRAG (optional)                       │  │
│  │  Gemini      │  │  Entity/relation extraction                │  │
│  │  OpenAI      │  │  GraphML + vector DBs                      │  │
│  │  Anthropic   │  │  Local / global / hybrid / naive query     │  │
│  │  NVIDIA NIM  │  └────────────────────────────────────────────┘  │
│  │  Ollama      │                                                   │
│  └──────────────┘                                                   │
└──────────────────────────────────┬──────────────────────────────────┘
                                   │
              ┌────────────────────┴────────────────────┐
              ▼                                         ▼
 ┌────────────────────────┐               ┌──────────────────────────┐
 │  PostgreSQL 16          │               │  Local filesystem         │
 │  + pgvector extension  │               │  .docintel/uploads/       │
 │                        │               │  .docintel_graph/         │
 │  docintel_chunks        │               │  (Docker volumes in prod) │
 │  organizations          │               └──────────────────────────┘
 │  users / invitations   │
 │  document_library      │
 │  query_history         │
 └────────────────────────┘
```

---

## Quick Start — Docker Compose

**Prerequisites:** Docker and Docker Compose, plus at least one LLM API key.

```bash
# 1. Clone the repository
git clone https://github.com/your-org/docintel.git
cd docintel

# 2. Create the environment file
cp .env.example .env
```

Edit `.env` and set at minimum:

```env
SECRET_KEY=<output of: python -c "import secrets; print(secrets.token_urlsafe(32))">
GEMINI_API_KEY=your_key_here          # or OPENAI_API_KEY, ANTHROPIC_API_KEY, etc.
DEFAULT_PROVIDER=gemini               # matches the key you provided
```

```bash
# 3. Start all services
docker compose up -d

# 4. Wait for the API to be healthy
docker compose logs -f api            # Ctrl-C when you see "Application startup complete"

# 5. Create the first super-admin account
curl -s -X POST http://localhost:8000/superadmin/bootstrap \
  -H "Content-Type: application/json" \
  -d '{"email":"admin@company.com","password":"changeme","full_name":"Platform Admin"}'

# 6. Open the web UI
open http://localhost:3000
```

> **First-time setup in the UI:**
> 1. Log in with your super-admin credentials
> 2. Go to **Admin → Settings** to configure your LLM provider and save API keys
> 3. Go to **Documents** to upload your first file
> 4. Go to **Ask AI** and start querying

---

## Manual Setup

### Backend

**Requirements:** Python 3.10+, PostgreSQL 16 with the `vector` extension

```bash
# Install core + server dependencies
pip install -e ".[server,postgres,office,ocr]"

# For knowledge graph support (optional, installs torch + lightrag)
pip install -e ".[graph]"

# For additional LLM providers
pip install -e ".[openai,anthropic]"

# OCR requires the Tesseract binary and poppler (for scanned PDFs)
# Ubuntu / Debian:
sudo apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils
# macOS:
brew install tesseract poppler
```

**Start the server:**

```bash
python -m docintel.server \
  --backend pgvector \
  --db-url postgresql://docintel:docintel@localhost:5432/docintel \
  --secret-key "$(python -c 'import secrets; print(secrets.token_urlsafe(32))')" \
  --provider gemini \
  --gemini-api-key "$GEMINI_API_KEY" \
  --cors-origins http://localhost:3000 \
  --port 8000
```

### Frontend

**Requirements:** Node.js 18+

```bash
cd web
npm install

# Development
NEXT_PUBLIC_API_URL=http://localhost:8000 npm run dev

# Production build
npm run build && npm start
```

---

## Configuration

### Environment Variables (`.env`)

| Variable | Required | Description |
|---|---|---|
| `SECRET_KEY` | **Yes** | 32-byte random string — signs JWTs and encrypts API keys. **Must be stable across restarts.** |
| `POSTGRES_USER` | Yes (prod) | PostgreSQL username |
| `POSTGRES_PASSWORD` | Yes (prod) | PostgreSQL password |
| `POSTGRES_DB` | Yes (prod) | PostgreSQL database name |
| `DATABASE_URL` | Yes (prod) | Full DSN, e.g. `postgresql://user:pass@host:5432/db` |
| `DEFAULT_PROVIDER` | No | Default LLM provider: `gemini` / `openai` / `anthropic` / `nvidia` / `ollama` |
| `GEMINI_API_KEY` | No | Google Gemini API key |
| `OPENAI_API_KEY` | No | OpenAI API key |
| `ANTHROPIC_API_KEY` | No | Anthropic API key |
| `NVIDIA_API_KEY` | No | NVIDIA NIM API key |

### Server CLI Flags

```
python -m docintel.server [OPTIONS]

  --host                HOST      Bind address (default: 0.0.0.0)
  --port                PORT      Listen port (default: 8000)
  --secret-key          KEY       JWT/Fernet secret (auto-generate if omitted — unstable)
  --provider            PROVIDER  LLM provider: gemini|openai|anthropic|ollama|nvidia
  --embedding-provider  PROVIDER  Override embedding provider (required for Anthropic)
  --gemini-api-key      KEY       Gemini API key (falls back to GEMINI_API_KEY env var)
  --openai-api-key      KEY       OpenAI API key (falls back to OPENAI_API_KEY env var)
  --anthropic-api-key   KEY       Anthropic API key (falls back to ANTHROPIC_API_KEY env var)
  --nvidia-api-key      KEY       NVIDIA NIM API key (falls back to NVIDIA_API_KEY env var)
  --backend             BACKEND   Vector store: memory|pgvector (default: memory)
  --db-url              DSN       PostgreSQL DSN — required for pgvector + auth
  --persist-dir         DIR       JSON persistence directory (default: .docintel)
  --rag-mode            MODE      Retrieval: vector|graph|hybrid (default: vector)
  --lightrag-dir        DIR       LightRAG working directory (default: .docintel_graph)
  --allowed-ingest-dirs DIR,...   Comma-separated whitelist for /ingest (empty = all)
  --rate-limit-rpm      N         Per-IP rate limit requests/minute (0 = disabled)
  --cors-origins        URL,...   Allowed CORS origins (default: http://localhost:3000)
  --log-level           LEVEL     INFO|DEBUG|WARNING|ERROR (default: INFO)
  --log-json            BOOL      Structured JSON logs (default: true)
```

### Config Dataclass (`docintel.Config`)

Key fields available when using the Python library directly:

| Field | Default | Description |
|---|---|---|
| `provider` | `"gemini"` | LLM provider |
| `chunk_size` | `600` | Approximate words per chunk |
| `chunk_overlap` | `80` | Overlap words between adjacent chunks |
| `min_chunk_size` | `80` | Discard chunks smaller than this |
| `top_k` | `5` | Default number of retrieved chunks |
| `vector_store` | `"memory"` | `"memory"` or `"pgvector"` |
| `embed_batch_size` | `20` | Texts per embedding API call |
| `max_retries` | `5` | API retry attempts |
| `rag_mode` | `"vector"` | `"vector"` / `"graph"` / `"hybrid"` |
| `pipeline_mode` | `"single"` | `"single"` or `"writer_reviewer"` |
| `ocr_enabled` | `True` | Auto-OCR scanned PDF pages |
| `ocr_min_chars_per_page` | `50` | Characters threshold below which a page is treated as scanned |

---

## LLM Providers

Each organization can configure and store keys for any number of providers simultaneously. Keys are encrypted with AES-128 (Fernet) before storage.

| Provider | Generation Model (default) | Embedding Model (default) | Notes |
|---|---|---|---|
| `gemini` | `gemini-2.5-flash` | `gemini-embedding-001` (3072d) | Best default choice |
| `openai` | `gpt-4o` | `text-embedding-3-large` (3072d) | |
| `anthropic` | `claude-opus-4-7` | — | Requires `--embedding-provider openai` or `ollama` |
| `nvidia` | `meta/llama-3.1-70b-instruct` | `nvidia/nv-embedqa-e5-v5` (1024d) | Requires NVIDIA NIM account |
| `ollama` | `llama3.2` | `nomic-embed-text` (768d) | Self-hosted, no API key needed |

**Changing the active provider:**

Via the web UI: **Admin → Settings → Active provider**

Via API:
```bash
curl -X PATCH http://localhost:8000/admin/settings \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"llm_provider": "openai", "openai_api_key": "sk-..."}'
```

> Changing the provider invalidates the pipeline cache immediately. The next request rebuilds the pipeline with the new provider.

---

## OCR Support

DocIntel automatically handles scanned documents and image files without any extra configuration.

### Scanned PDFs

When a PDF page yields fewer than 50 characters of text, it is automatically re-processed with Tesseract OCR. Text-rich pages use direct extraction; OCR only runs on sparse/image pages.

```
PDF upload → pypdf extraction (per page)
  ├── Page has ≥ 50 chars  →  use extracted text directly
  └── Page has < 50 chars  →  pdf2image (200 DPI) → Tesseract → OCR text
```

### Image Uploads

The following image formats can be uploaded directly as documents. Text is extracted entirely via OCR.

| Format | Extension |
|---|---|
| JPEG | `.jpg`, `.jpeg` |
| PNG | `.png` |
| TIFF (multi-page) | `.tiff`, `.tif` |
| BMP | `.bmp` |
| WebP | `.webp` |
| GIF | `.gif` |

Multi-page TIFF files produce one searchable chunk per frame.

### OCR Requirements

OCR requires the Tesseract binary and poppler utilities to be installed on the server:

```bash
# Ubuntu / Debian / Docker
apt-get install tesseract-ocr tesseract-ocr-eng poppler-utils

# macOS
brew install tesseract poppler
```

These are pre-installed in the provided `Dockerfile.api`. For additional languages:

```bash
# Example: add German and French OCR support
apt-get install tesseract-ocr-deu tesseract-ocr-fra
```

To disable OCR (for performance or when not needed):

```python
di.configure(ocr_enabled=False)
```

---

## Pipeline Modes

The pipeline mode controls how LLM calls are orchestrated when answering questions.

### Single LLM (default)

One model call generates the answer directly from retrieved context. Fastest and most cost-efficient.

```
User question + retrieved chunks → LLM → Answer
```

### Writer + Reviewer

Two sequential LLM calls for higher accuracy and better citation handling:

1. **Writer**: Drafts an answer from the retrieved context
2. **Reviewer**: Fact-checks the draft against the original context, corrects citations, and improves completeness

```
User question + context → Writer LLM → Draft
Draft + context         → Reviewer LLM → Final answer
```

Configure per organisation via **Admin → Settings → Pipeline configuration**, or via API:

```bash
curl -X PATCH http://localhost:8000/admin/settings \
  -H "Authorization: Bearer $TOKEN" \
  -d '{"pipeline_mode": "writer_reviewer"}'
```

---

## Python Library API

DocIntel can also be used as a standalone Python library without the HTTP server.

### Installation

```bash
pip install -e ".[office]"   # for DOCX/XLSX/PPTX support
pip install -e ".[ocr]"      # for OCR support (also needs tesseract binary)
```

### Module-level API

```python
import docintel as di

# Configure once per process
di.configure(
    provider="gemini",
    gemini_api_key="AIza...",
    chunk_size=600,
    top_k=5,
)

# Ingest a document
doc = di.ingest("report.pdf")
print(f"Ingested {doc.chunk_count} chunks")

# Ask a question
result = di.ask("What were the key findings?")
print(result.answer)
for s in result.sources:
    print(f"  [{s.score:.2%}] page {s.chunk.metadata.get('page')} — {s.chunk.text[:80]}")

# Semantic search (returns chunks without generation)
results = di.search("operating temperature range")
for r in results:
    print(r.score, r.chunk.text[:100])

# Clean up
di.delete("report.pdf")
```

### Class-based API

```python
from docintel import Pipeline
from docintel._config import Config

config = Config(
    provider="openai",
    openai_api_key="sk-...",
    vector_store="pgvector",
    db_url="postgresql://user:pass@localhost:5432/db",
    chunk_size=800,
    top_k=8,
    pipeline_mode="writer_reviewer",
)

pipeline = Pipeline(config)

# Ingest with collection namespacing
pipeline.ingest("safety_manual.pdf", tenant_id="acme:safety")

# Query within a specific collection
result = pipeline.ask(
    "What PPE is required for zone 3?",
    tenant_id="acme:safety",
)
print(result.answer)

# Multi-document search with doc_id filter
results = pipeline.search(
    "emergency shutdown procedure",
    tenant_id="acme:safety",
    doc_ids=["doc-uuid-1", "doc-uuid-2"],
)
```

### Supported Formats (Python API)

| Category | Extensions |
|---|---|
| PDF | `.pdf` |
| Office | `.docx`, `.doc`, `.xlsx`, `.xls`, `.pptx`, `.ppt` |
| Text | `.txt`, `.md`, `.rst`, `.log` |
| Data | `.csv` |
| Web | `.html`, `.htm` |
| Images (OCR) | `.png`, `.jpg`, `.jpeg`, `.tiff`, `.tif`, `.bmp`, `.webp`, `.gif` |

---

## HTTP Server

The REST API is available at `http://localhost:8000`. Interactive Swagger UI is at `/docs`.

### Authentication

All endpoints (except `/health`, `/auth/register`, `/auth/login`, `/auth/refresh`, `/auth/accept-invite`, and `/superadmin/bootstrap`) require a valid JWT access token:

```
Authorization: Bearer <access_token>
```

Tokens expire after **1 hour**. Use the refresh endpoint to obtain a new access token with your 7-day refresh token.

### Core Endpoints

| Method | Path | Auth | Description |
|---|---|---|---|
| `GET` | `/health` | None | Liveness check |
| `POST` | `/auth/register` | None | Create org + admin user |
| `POST` | `/auth/login` | None | Authenticate, get tokens |
| `POST` | `/auth/refresh` | None | Exchange refresh token |
| `GET` | `/auth/me` | Bearer | Current user profile |
| `POST` | `/upload` | Bearer | Upload a file (background ingest) |
| `GET` | `/documents` | Bearer | List documents |
| `DELETE` | `/documents/{id}` | Bearer | Delete document |
| `GET` | `/documents/{id}/file` | Bearer | Stream file (PDF inline) |
| `POST` | `/ask` | Bearer | RAG question answering |
| `POST` | `/search` | Bearer | Semantic vector search |
| `GET` | `/history` | Bearer | Query history |
| `GET` | `/admin/settings` | Admin | Org LLM configuration |
| `PATCH` | `/admin/settings` | Admin | Update org configuration |
| `POST` | `/admin/settings/validate` | Admin | Test active API key |
| `GET` | `/admin/users` | Admin | Team members + invitations |
| `POST` | `/auth/invite` | Admin | Send invitation email token |
| `POST` | `/superadmin/bootstrap` | None* | Create first superadmin |

*One-time only — returns 409 if a superadmin already exists.

Full API reference: [docs/api.md](docs/api.md)

### Example: Upload and Ask

```bash
# Upload a document
curl -X POST http://localhost:8000/upload \
  -H "Authorization: Bearer $TOKEN" \
  -F "file=@report.pdf" \
  -F "collection_id=default"

# Ask a question
curl -X POST http://localhost:8000/ask \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{
    "question": "What is the maximum load capacity?",
    "tenant_id": "org-uuid:default"
  }'
```

---

## Roles and Permissions

| Role | Scope | Capabilities |
|---|---|---|
| `superadmin` | Platform | Manage all organisations, users, and platform settings |
| `org_admin` | Organisation | Manage team, configure LLM/keys, upload/delete documents |
| `manager` | Organisation | Upload and delete documents, run queries |
| `user` | Organisation | Upload documents, run queries |
| `viewer` | Organisation | Run queries only (no upload) |

**Inviting a team member:**

```bash
# Generate invite token (org_admin or above)
curl -X POST http://localhost:8000/auth/invite \
  -H "Authorization: Bearer $TOKEN" \
  -H "Content-Type: application/json" \
  -d '{"email": "colleague@company.com", "role": "user"}'

# The invitee accepts with the token they receive
curl -X POST http://localhost:8000/auth/accept-invite \
  -H "Content-Type: application/json" \
  -d '{"token":"<token>","full_name":"Jane Doe","password":"securepass"}'
```

---

## Knowledge Graph

DocIntel optionally integrates [LightRAG](https://github.com/HKUDS/LightRAG) for knowledge-graph-enhanced retrieval. When enabled, entities and relationships are extracted from documents and stored as a graph, allowing multi-hop reasoning.

**Requires:**
```bash
pip install -e ".[graph]"
```

**Retrieval modes when graph is enabled:**

| Mode | Description |
|---|---|
| `vector` | Pure semantic similarity (default) |
| `graph` | Graph-based entity and relation traversal |
| `hybrid` | Combine vector and graph results (recommended with graph) |

**Enable in Docker Compose:**

The default `docker-compose.yml` already runs with `--rag-mode hybrid`. Graph rebuilding can be triggered from the **Graph** page in the UI or via API:

```bash
curl -X POST http://localhost:8000/graph/rebuild \
  -H "Authorization: Bearer $TOKEN"

# Check progress
curl http://localhost:8000/graph/rebuild/status \
  -H "Authorization: Bearer $TOKEN"
```

---

## Documentation

| Document | Description |
|---|---|
| [docs/api.md](docs/api.md) | Complete HTTP API reference — all 35 endpoints with request/response schemas |
| [docs/architecture.md](docs/architecture.md) | System architecture, data flow, multi-tenancy design |
| [docs/deployment.md](docs/deployment.md) | Production deployment — Docker, SSL, secrets, scaling |

---

## Development

```bash
# Install dev dependencies
pip install -e ".[server,postgres,office,ocr,dev]"

# Run tests
pytest

# Lint
ruff check docintel/

# Run the API server in dev mode (auto-reload)
python -m docintel.server --backend memory --log-level DEBUG
```

---

## License

MIT — see [LICENSE](LICENSE) for details.
