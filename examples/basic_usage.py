"""
Basic usage of the docintel framework.
Run from the repo root:  python examples/basic_usage.py

Set your key first:
    export GEMINI_API_KEY="your-key-here"   # Linux/macOS
    set GEMINI_API_KEY=your-key-here        # Windows
"""

import os

import docintel as di
from docintel import Pipeline

# ── 1. Configure once ──────────────────────────────────────────────────────
di.configure(gemini_api_key=os.environ["GEMINI_API_KEY"])

# ── 2. Ingest documents ────────────────────────────────────────────────────
# di.ingest("path/to/maintenance_manual.pdf")
# di.ingest("path/to/inspection_report.pdf", tenant_id="plant_b")

# ── 3. Ask questions (RAG) ─────────────────────────────────────────────────
# result = di.ask("What are the hydraulic pump maintenance procedures?")
# print(result.answer)
# print(f"\nSources: {[s.document_path for s in result.sources]}")

# ── 4. Similarity search ───────────────────────────────────────────────────
# hits = di.search("pressure tolerance specifications", top_k=3)
# for hit in hits:
#     print(f"Score: {hit.score:.3f} | {hit.chunk.metadata.get('breadcrumb')}")

# ── 5. Stats ───────────────────────────────────────────────────────────────
print(di.stats())


p = Pipeline(gemini_api_key=os.environ["GEMINI_API_KEY"])
# p.ingest("document.pdf", tenant_id="company_a")
# result = p.ask("What safety procedures apply to the boiler?", tenant_id="company_a")
# print(result.answer)

print("docintel framework loaded successfully.")
