# Document Analyst Agent

A ReAct agent that **extracts** structured data from invoices/contracts, **stores**
them (with embeddings) in PostgreSQL/pgvector, and **answers questions grounded in
those documents** via RAG — citing the source.

It does four things:

1. **Extraction** — load a PDF/DOCX/TXT/CSV, chunk it, extract structured fields
   into Pydantic schemas (`Invoice`/`Contract`), save JSON.
2. **Storage** — `Document` + `DocumentChunk` (one-to-many) in PostgreSQL with
   pgvector, via Alembic migrations and a Repository layer.
3. **RAG** — embed each chunk (sentence-transformers), cosine similarity search
   with an HNSW index.
4. **Agent** — a `search_documents` tool lets the agent answer from the indexed
   documents and cite the source filename.

---

## Prerequisites

- **Docker Desktop** running (for PostgreSQL + pgvector).
- **Python 3.11** and the project dependencies (see step 1).
- An **Anthropic API key** (the agent and extraction call the LLM). The embedding
  step runs locally and is free.

---

## Quick start (run it from scratch)

All commands run from this `homework_2/` folder.

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

> Installs LangChain + Anthropic, document loaders, SQLAlchemy + pgvector + Alembic,
> and sentence-transformers (this pulls in `torch`, which is large).

### 2. Configure secrets

```bash
cp .env_example .env
# edit .env and set: ANTHROPIC_API_KEY=sk-ant-...
```

`.env` already contains the database settings (`DATABASE_URL`, `POSTGRES_*`).

### 3. Start the database

```bash
docker compose up -d --wait
```

> Starts PostgreSQL with the pgvector extension and waits until it is healthy.
> Check anytime with `docker compose ps`.

### 4. Create the tables (migrations)

```bash
alembic upgrade head
```

> Enables the `vector` extension and creates the `documents` and `document_chunks`
> tables. Verify with `alembic current` (should print `0002_document_chunks (head)`).

### 5. (Optional) Build the HNSW index

```bash
python -m db.create_index
```

> Adds an HNSW index for fast similarity search. Not required for a few documents.

### 6. Run the tests

```bash
pytest -q
```

> Expect `58 passed`. Pure tests need nothing; database/RAG tests run real CRUD and
> similarity search and **skip automatically** if the database is not up.

---

## Try it

### A. Extract structured data from a document

```bash
python3 -c "from extraction import extract_document; inv = extract_document('samples/factura_001.txt','factura'); print(inv.numar, inv.total, inv.furnizor)"
```

> Prints `FV-2024-001 18088.0 SC TechPro Solutions SRL` and writes
> `extracted_data/factura/FV-2024-001.json`. (Calls the LLM.)

### B. Index documents for question-answering

The agent can answer about document content only after you index some documents:

```bash
python3 -c "
from rag import index_documents
docs = index_documents(['samples/contract_servicii.txt','samples/contract_consultanta.txt','samples/factura_001.txt'])
print('indexed:', [d.filename for d in docs])
"
```

> Loads, chunks, embeds, and stores each file (Document + chunks), with a progress
> bar over the files. Idempotent: running it again does not duplicate. (Local
> embeddings, no LLM call.) For a single file, use `index_document(path)`.

### C. Ask the agent (interactive)

```bash
python agent.py
```

Then type questions, for example:

```
You> Ce clauze de reziliere avem?
You> Care este totalul facturii FV-2024-001?
You> Care sunt obligatiile prestatorului din contractul de servicii?
You> Cât face 15200 * 0.19?
You> exit
```

> Tool calls are shown inline (`[tool] search_documents(...)` → `[result] ...`),
> then the final answer with the cited source `[filename]`. The agent picks the
> right tool by itself: `search_documents` for document content, `calculator` for
> math, `extract_invoice_tool` / `extract_contract_tool` to process a new file.
> Commands: `reset` clears history, `exit` / `quit` leaves.

One-off, non-interactive:

```bash
python3 -c "from agent import ask; print(ask('Care este totalul facturii FV-2024-001?'))"
```

---

## Inspect the database (optional)

```bash
docker compose exec db psql -U analyst -d document_analyst
```

```sql
\dt                                  -- list tables
SELECT id, filename FROM documents;  -- indexed documents
SELECT d.filename, count(c.id) FROM documents d
  JOIN document_chunks c ON c.document_id = d.id GROUP BY d.filename;  -- chunks per doc
\q
```

## Stop / reset

```bash
docker compose stop      # stop, keep the data
docker compose down -v   # remove container + data (full reset)
```

---

## Project structure

```
homework_2/
├── agent.py                 # LLMFactory, ReAct loop, entry points (ask/chat)
├── docker-compose.yml       # PostgreSQL + pgvector
├── alembic.ini              # Alembic config (migrations live in db/alembic/)
├── tools/                   # calculator, datetime, web_search,
│                            #   extract_invoice/contract, search_documents
├── extraction/              # loaders, schemas, chunking, pipeline (Load→Chunk→Extract→Save)
├── db/                      # database, models, repositories, exceptions, create_index
│   └── alembic/             #   migrations (documents, document_chunks)
├── rag/                     # service (embed/search), indexing (index_document/index_documents)
├── prompts/                 # planner.yaml + task prompts (YAML + Jinja2)
├── samples/                 # example invoices/contracts
└── tests/                   # pure + DB-integration tests (auto-skip without DB)
```

## How it works

- **Extraction:** `load_document()` resolves a loader by file extension; large text
  is chunked; `ExtractionPipeline.process()` calls `llm.with_structured_output(schema)`;
  `save_json()` writes per-type JSON.
- **Storage + RAG:** `index_document()` loads + chunks a file, embeds the chunks, and
  stores a `Document` plus its `DocumentChunk`s in one transaction (idempotent on
  filename). `RAGService.search(query, top_k)` embeds the query and runs cosine
  similarity search; `search_documents` exposes this to the agent.
- **Language:** answers follow the user's language; the embedding model is multilingual
  (Romanian-friendly).

## Design patterns

- **Registry** — tools, prompts, loaders, extraction routing
- **Repository** — `DocumentRepository`, `ChunkRepository` (+ `transaction()` unit of work)
- **Decorator** — `@register_tool`
- **Factory** — `LLMFactory` (Anthropic / OpenAI / Google / Ollama)
- **Pipeline** — `ExtractionPipeline` (Load → Chunk → Extract → Save) + `index_document`
