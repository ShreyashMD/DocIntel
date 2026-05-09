# docintel

**Industrial Document Analysis Framework** — ingest, chunk, embed, and query technical documents with a single import.

```python
import docintel as di

di.configure(gemini_api_key="...")
di.ingest("maintenance_manual.pdf")

result = di.ask("What is the maximum operating pressure?")
print(result.answer)
```

Built for industrial environments: maintenance manuals, compliance reports, inspection logs, CAD drawings, and multi-tenant enterprise deployments.

---

## Table of Contents

- [Features](#features)
- [Installation](#installation)
- [Quickstart](#quickstart)
- [API Reference](#api-reference)
- [Configuration](#configuration)
- [Multi-Tenancy](#multi-tenancy)
- [Supported File Types](#supported-file-types)
- [Optional Extras](#optional-extras)
- [Scaling Guide](#scaling-guide)
- [Architecture](#architecture)
- [Roadmap](#roadmap)

---

## Features

- **One-import API** — `di.configure()`, `di.ingest()`, `di.ask()`, `di.search()`
- **Hierarchical chunking** — preserves document structure with breadcrumb trails
- **Contextual Retrieval** — document summary prepended to every chunk before embedding
- **Multi-tenant isolation** — separate vector namespaces per organisation
- **Disk-persistent index** — survives restarts, no database required for Phase 1
- **Rate-limit resilient** — exponential backoff with `tenacity` on all API calls
- **Swappable backends** — memory → pgvector → Qdrant → Milvus without changing your code
- **Optional OCR & CAD** — docTR layout analysis and ezdxf CAD parsing as optional extras

---

## Installation

**Prerequisites:** Python 3.9+, a [Gemini API key](https://aistudio.google.com/app/apikey) (free tier works).

```bash
# From the repo root
pip install -e ./docintel

# Or once published to PyPI
pip install docintel
```

Set your API key as an environment variable (never hardcode it):

```bash
# Linux / macOS
export GEMINI_API_KEY="your-key-here"

# Windows (Command Prompt)
set GEMINI_API_KEY=your-key-here

# Windows (PowerShell)
$env:GEMINI_API_KEY="your-key-here"
```

---

## Quickstart

### Module-level API (simplest)

```python
import os
import docintel as di

di.configure(gemini_api_key=os.environ["GEMINI_API_KEY"])

# Ingest documents
di.ingest("hydraulic_manual.pdf")
di.ingest("inspection_log.txt")

# Ask questions (RAG)
result = di.ask("What are the daily maintenance checks for the hydraulic pump?")
print(result.answer)

# Show where the answer came from
for source in result.sources:
    print(f"  [{source.score:.2f}] {source.chunk.metadata['breadcrumb']}")
```

### Class-based API (more control)

```python
from docintel import Pipeline

p = Pipeline(
    gemini_api_key=os.environ["GEMINI_API_KEY"],
    persist_dir=".myproject",
    top_k=5,
)

p.ingest("schematic.pdf", tenant_id="plant_a")
p.ingest("compliance_report.pdf", tenant_id="plant_b")

# Each tenant is fully isolated
result_a = p.ask("What are the pressure tolerances?", tenant_id="plant_a")
result_b = p.ask("What are the compliance failures?", tenant_id="plant_b")
```

### Semantic search (without generation)

```python
hits = di.search("hydraulic pump cavitation noise", top_k=5)

for hit in hits:
    print(f"Score:    {hit.score:.3f}")
    print(f"Section:  {hit.chunk.metadata['breadcrumb']}")
    print(f"Document: {hit.document_path}")
    print(f"Text:     {hit.chunk.text[:200]}")
    print()
```

---

## API Reference

### `di.configure()`

Initialises the default global pipeline. Call once at startup.

```python
di.configure(
    gemini_api_key: str,           # required
    generation_model: str,         # default: "gemini-2.5-flash"
    embedding_model: str,          # default: "gemini-embedding-001"
    chunk_size: int,               # default: 600 (words)
    chunk_overlap: int,            # default: 80 (words)
    top_k: int,                    # default: 5
    vector_store: str,             # "memory" | "pgvector" | "qdrant"
    persist_dir: str | None,       # default: ".docintel/"
    db_url: str | None,            # required for pgvector
    qdrant_url: str | None,        # required for qdrant
)
```

### `di.ingest(path, ...)`

Extracts, chunks, embeds, and indexes a document.

```python
doc = di.ingest(
    path: str,             # Path to file
    tenant_id: str,        # default: "default"
    summarize: bool,       # Prepend doc summary to chunks (Contextual Retrieval). default: True
    verbose: bool,         # Print progress. default: True
)
# Returns a Document object
```

### `di.ask(question, ...)`

Retrieves relevant chunks then generates an answer with Gemini.

```python
result = di.ask(
    question: str,
    tenant_id: str,        # default: "default"
    top_k: int | None,     # override config default
)

result.answer      # str — generated answer
result.sources     # list[SearchResult] — ranked source chunks
result.question    # str — original question
result.model       # str — model used for generation
```

### `di.search(query, ...)`

Pure vector similarity search — no generation.

```python
hits = di.search(
    query: str,
    tenant_id: str,
    top_k: int | None,
)

# Each hit:
hit.score           # float — cosine similarity (0–1)
hit.chunk.text      # str — raw chunk text
hit.chunk.metadata  # dict — breadcrumb, page, doc_path, sub_chunk_index
hit.document_path   # str — source file path
hit.tenant_id       # str
```

### `di.delete(path, tenant_id)`

Removes all chunks for a specific document from the index.

```python
di.delete("old_manual.pdf", tenant_id="plant_a")
```

### `di.stats()`

Returns basic store statistics.

```python
di.stats()
# → {"total_chunks": 1842, "tenants": ["plant_a", "plant_b"]}
```

---

## Configuration

All config fields with their defaults:

| Parameter | Default | Description |
|---|---|---|
| `gemini_api_key` | — | **Required.** Gemini API key. |
| `generation_model` | `gemini-2.5-flash` | Model for RAG answers and summaries. |
| `embedding_model` | `gemini-embedding-001` | Embedding model (3072 dimensions). |
| `chunk_size` | `600` | Target words per chunk. |
| `chunk_overlap` | `80` | Word overlap between adjacent chunks. |
| `min_chunk_size` | `80` | Discard chunks shorter than this. |
| `top_k` | `5` | Chunks to retrieve per query. |
| `vector_store` | `memory` | Backend: `memory`, `pgvector`, `qdrant`. |
| `persist_dir` | `.docintel/` | Where the memory store saves its index JSON. |
| `db_url` | `None` | PostgreSQL URL (required for `pgvector`). |
| `qdrant_url` | `None` | Qdrant server URL (required for `qdrant`). |
| `embed_batch_size` | `20` | Texts per Gemini embedding API call. |
| `max_retries` | `5` | Retry attempts on API failures. |

---

## Multi-Tenancy

Every operation accepts a `tenant_id`. Data is always isolated — a search for `tenant_id="plant_a"` can never return results from `tenant_id="plant_b"`.

```python
# Ingest for different organisations
di.ingest("plant_a_manual.pdf", tenant_id="plant_a")
di.ingest("plant_b_report.pdf", tenant_id="plant_b")

# Query is automatically scoped
di.ask("What are the pressure limits?", tenant_id="plant_a")
di.ask("What are the pressure limits?", tenant_id="plant_b")

# Delete one tenant's document without affecting others
di.delete("plant_a_manual.pdf", tenant_id="plant_a")
```

At the **memory** backend, tenants are partitioned by key in a single JSON index. When you migrate to **Qdrant**, isolation is enforced via payload filtering. When you migrate to **Milvus**, you get collection-level physical separation.

---

## Supported File Types

| Extension | Extractor | Notes |
|---|---|---|
| `.pdf` | `PdfExtractor` (pypdf) | Text-based PDFs. For scanned PDFs install the `[ocr]` extra. |
| `.txt` | `TextExtractor` | Plain text, split by blank lines. |
| `.md` | `TextExtractor` | Markdown files. |
| `.rst` | `TextExtractor` | reStructuredText. |
| `.log` | `TextExtractor` | Log files. |
| `.dxf` | `CadExtractor` (ezdxf) | CAD drawings — requires `[cad]` extra. |

---

## Optional Extras

### OCR for scanned PDFs

```bash
pip install "docintel[ocr]"
```

Installs [docTR](https://github.com/mindee/doctr) for layout-aware OCR on noisy scans. docTR outputs a hierarchical page model (Pages → Blocks → Lines → Words) that feeds directly into the hierarchical chunker.

```python
# Enable OCR mode during ingest
doc = p.ingest("scanned_inspection_report.pdf", ocr=True)
```

### CAD / DXF drawings

```bash
pip install "docintel[cad]"
```

Installs [ezdxf](https://ezdxf.readthedocs.io) for parsing DXF/DWG engineering drawings. The extractor reads the HEADER section (units, timestamps, encoding), geometric entities (lines, arcs, circles, polylines), and title block text entities (part numbers, tolerances, drawing IDs).

```python
doc = p.ingest("hydraulic_assembly.dxf")
result = p.ask("How many bore holes are specified in the assembly?")
```

### PostgreSQL + pgvector

```bash
pip install "docintel[postgres]"
```

```python
di.configure(
    gemini_api_key=os.environ["GEMINI_API_KEY"],
    vector_store="pgvector",
    db_url="postgresql://user:password@localhost:5432/docintel",
)
```

---

## Scaling Guide

docintel is built on a three-phase architecture. You start with zero infrastructure and add components only when load demands it.

---

### Phase 1 — Zero-Infrastructure MVP (default)

**Stack:** Gemini API · pypdf · In-memory vector store · JSON persistence

This is what you get out of the box. No Docker, no database, no message broker.

**Suitable for:** up to ~50,000 document chunks, single-server deployment, internal tools.

**Bottleneck:** The entire index loads into RAM. Gemini free-tier rate limits cap throughput at ~10–15 requests per minute.

---

### Phase 2 — Production-Ready Distributed System

Swap individual components by changing config — your application code stays identical.

#### 2a. Upgrade vector storage to Qdrant

Qdrant is written in Rust, purpose-built for vector search, and handles hundreds of millions of vectors with advanced memory compression.

```bash
# Start Qdrant
docker run -p 6333:6333 qdrant/qdrant
```

```python
di.configure(
    gemini_api_key=os.environ["GEMINI_API_KEY"],
    vector_store="qdrant",
    qdrant_url="http://localhost:6333",
)
```

Multi-tenancy in Qdrant uses **payload partitioning** inside a single collection. Every vector is tagged with `group_id=tenant_id` and every search request filters on it. For tenants with very large datasets, Qdrant supports "Tenant Promotion" — transparently sharding a single tenant onto a dedicated node without downtime.

#### 2b. Add PostgreSQL for metadata and structured results

```bash
docker run -e POSTGRES_PASSWORD=secret -p 5432:5432 postgres
```

```python
di.configure(
    gemini_api_key=os.environ["GEMINI_API_KEY"],
    vector_store="pgvector",
    db_url="postgresql://postgres:secret@localhost:5432/docintel",
)
```

pgvector adds HNSW and IVFFlat vector search directly to PostgreSQL tables. This is ideal when you want atomic transactions between your document metadata and vector index, and your dataset stays under ~5 million chunks.

#### 2c. Add Apache Kafka for durable ingestion

When users upload multi-thousand-page documents concurrently, synchronous ingestion will exhaust memory. Kafka decouples upload from processing:

```
Client → FastAPI (writes file to MinIO, publishes event) → Kafka topic
                                                                  ↓
                                             Worker pool (consumes events, runs pipeline)
```

The Kafka layer acts as a backpressure mechanism — no matter how many documents are uploaded simultaneously, workers consume at a controlled rate. If a worker crashes mid-document, the event remains in Kafka and is reprocessed.

```bash
docker compose up kafka zookeeper
```

```python
# Producer (in your FastAPI route)
from kafka import KafkaProducer
import json

producer = KafkaProducer(bootstrap_servers="localhost:9092")
producer.send("docintel.ingest", json.dumps({
    "path": "s3://bucket/manual.pdf",
    "tenant_id": "plant_a",
}).encode())

# Consumer (in your worker process)
from kafka import KafkaConsumer

consumer = KafkaConsumer("docintel.ingest", bootstrap_servers="localhost:9092")
for message in consumer:
    job = json.loads(message.value)
    di.ingest(job["path"], tenant_id=job["tenant_id"])
```

#### 2d. Add Dagster for pipeline orchestration

Dagster replaces ad-hoc worker scripts with a fully observable, asset-centric orchestration layer. It tracks exactly which pages have been processed, resumes from the point of failure (not from page 1), and provides a live dashboard for monitoring pipeline health.

```bash
pip install dagster dagster-webserver
```

```python
from dagster import asset, define_asset_job

@asset
def extracted_pages(context, raw_document):
    return di._pipeline._extract(raw_document["path"])

@asset
def embedded_chunks(context, extracted_pages):
    # chunking + embedding as a tracked data asset
    ...

document_pipeline = define_asset_job("document_pipeline", selection=[extracted_pages, embedded_chunks])
```

Key advantage over Airflow: Dagster's asset-aware model means "resume from page 4,500 of 5,000" rather than "restart the entire 5,000-page document from scratch."

#### 2e. Add Keycloak for enterprise authentication

For multi-tenant B2B deployments, Keycloak provides native realm-based isolation. Each industrial client gets their own Keycloak realm — a completely separate user directory, credential store, and role hierarchy.

```bash
docker run -p 8080:8080 -e KEYCLOAK_ADMIN=admin quay.io/keycloak/keycloak:latest start-dev
```

Roles (`Admin`, `Manager`, `Analyst`, `Viewer`) are configured in the Keycloak console. Your FastAPI routes read the signed JWT to enforce access:

```python
from fastapi import Depends, HTTPException
from fastapi.security import OAuth2AuthorizationCodeBearer

oauth2 = OAuth2AuthorizationCodeBearer(
    authorizationUrl="http://keycloak:8080/realms/{realm}/protocol/openid-connect/auth",
    tokenUrl="http://keycloak:8080/realms/{realm}/protocol/openid-connect/token",
)

@app.post("/ingest")
async def ingest_endpoint(token=Depends(oauth2)):
    # Keycloak JWT is verified; roles extracted from token claims
    ...
```

---

### Phase 3 — Enterprise Intelligence Layer

#### Milvus for billion-scale vector storage

When Qdrant approaches its limits (~hundreds of millions of vectors), migrate to Milvus. Milvus separates storage from computation, scales elastically on Kubernetes, and supports GPU-accelerated indexing.

Multi-tenancy strategy for B2B platforms: **Collection-Level isolation** gives each client a physically separate collection with its own RBAC policy, supporting over 65,000 independent tenants on a single cluster.

```bash
helm install milvus milvus/milvus --set cluster.enabled=true
```

```python
di.configure(
    gemini_api_key=os.environ["GEMINI_API_KEY"],
    vector_store="milvus",
    milvus_uri="http://milvus:19530",
)
```

#### Anomaly detection for visual inspection streams

Computer vision models (Autoencoders, One-class classifiers, Vision Transformers) detect defects in continuous visual feeds without requiring labelled defect catalogs. They establish a "normal" reconstruction baseline — deviations trigger anomaly flags.

Multimodal LLMs (e.g. Qwen2-VL-7B) then reason over the flagged frames to generate human-readable anomaly descriptions that are appended to compliance documents.

#### PDF compliance report generation

Generate pixel-perfect, branded PDF reports from extracted data using Playwright + Paged.js:

```bash
pip install playwright
playwright install chromium
```

```python
# Generate HTML report, then render to PDF via headless browser
from playwright.sync_api import sync_playwright

with sync_playwright() as pw:
    browser = pw.chromium.launch()
    page = browser.new_page()
    page.set_content(render_report_html(result))
    page.pdf(path="compliance_report.pdf", format="A4")
```

---

### Scaling Summary

| Metric | Phase 1 | Phase 2 | Phase 3 |
|---|---|---|---|
| **Chunks** | < 50K | < 500M | Billions |
| **Tenants** | Any (logical) | < 65K (Qdrant) | Millions (Milvus) |
| **Ingestion** | Synchronous | Kafka-backed async | Distributed workers |
| **Orchestration** | None | Dagster DAGs | Dagster + Kubernetes |
| **Auth** | JWT (DIY) | Keycloak realms | Keycloak + LDAP/AD |
| **Infra** | Zero | Docker Compose | Helm / Kubernetes |

---

## Architecture

```
                     ┌─────────────────────────────────────────────────┐
                     │                   docintel                      │
                     │                                                 │
  Document ──────►  │  Extractor  ──►  Chunker  ──►  Embedder        │
  (PDF/TXT/DXF)     │                                     │           │
                     │                                     ▼           │
                     │                              VectorStore        │
                     │                         (memory/pgvector/       │
                     │                          Qdrant/Milvus)         │
                     │                                     │           │
  Question ──────►  │  embed_query  ──►  search  ──►  GeminiClient ──► Answer
                     │                                                 │
                     └─────────────────────────────────────────────────┘
```

**Clean Architecture layers** (dependency inversion — outer layers depend on inner, never reverse):

```
┌─────────────────────────────────┐
│  Presentation  (Pipeline API)   │  ← di.ingest(), di.ask(), di.search()
├─────────────────────────────────┤
│  Application   (_pipeline.py)   │  ← orchestrates use cases
├─────────────────────────────────┤
│  Infrastructure                 │  ← GeminiClient, MemoryVectorStore,
│  (llm/, storage/, extractors/)  │    PdfExtractor, HierarchicalChunker
├─────────────────────────────────┤
│  Domain        (core/entities)  │  ← Document, Chunk, SearchResult
│  (framework-free)               │    QueryResult — pure Python dataclasses
└─────────────────────────────────┘
```

This means: swapping Qdrant for Milvus, or Gemini for a local Ollama model, requires changing **only** the Infrastructure layer. The Pipeline API and your application code stay untouched.

---

## Roadmap

- [ ] **Phase 2** — Qdrant and pgvector storage adapters
- [ ] **Phase 2** — Kafka consumer integration
- [ ] **Phase 2** — Dagster asset definitions
- [ ] **Phase 2** — Keycloak JWT middleware
- [ ] **Phase 2** — Novu notification hooks (alert when long ingestion completes)
- [ ] **Phase 3** — Milvus adapter with collection-level multi-tenancy
- [ ] **Phase 3** — docTR OCR integration for scanned PDFs
- [ ] **Phase 3** — ezdxf CAD extractor with VLM dimensional reasoning
- [ ] **Phase 3** — Anomaly detection pipeline (Autoencoder + Qwen2-VL)
- [ ] **Phase 3** — Playwright PDF compliance report generation
- [ ] **Phase 3** — FastAPI reference server with Keycloak RBAC
- [ ] **Phase 3** — Next.js frontend with Shadcn UI

---

## Contributing

1. Fork the repository
2. Create a feature branch: `git checkout -b feat/qdrant-adapter`
3. Install dev dependencies: `pip install -e "docintel[dev]"`
4. Run tests: `pytest docintel/tests/`
5. Open a pull request

---

## License

MIT — see [LICENSE](LICENSE).
