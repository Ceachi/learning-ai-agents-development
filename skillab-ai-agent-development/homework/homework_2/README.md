# Document Analyst Agent

A ReAct agent that **extracts** structured data from invoices/contracts, **stores**
them (with embeddings) in PostgreSQL/pgvector, and **answers questions grounded in
those documents** via RAG — citing the source.

What it does:

1. **Extraction** — load a PDF/DOCX/TXT/CSV, chunk it, extract structured fields
   into Pydantic schemas (`Invoice`/`Contract`), save JSON.
2. **Storage** — `Document` + `DocumentChunk` (one-to-many) in PostgreSQL with
   pgvector, via Alembic migrations and a Repository layer.
3. **RAG** — embed each chunk (sentence-transformers), cosine similarity search
   with an HNSW index.
4. **Agent** — a `search_documents` tool lets the agent answer from the indexed
   documents and cite the source filename.

---

## Contents

- [Prerequisites](#prerequisites)
- [1. Direct setup (recommended)](#1-direct-setup-recommended) — install and run; the database, index and sample documents are set up for you.
- [2. Step-by-step (optional)](#2-step-by-step-optional) — reset everything and run each step, including the test suite.
- [Interacting with the agent](#interacting-with-the-agent)
- [Inspect the database](#inspect-the-database)
- [Stop / reset](#stop--reset)
- [Project structure](#project-structure) · [How it works](#how-it-works)

---

## Prerequisites

- **Docker Desktop** running (for PostgreSQL + pgvector).
- **Python 3.11**.
- An **Anthropic API key** — the agent and extraction call the LLM. The embedding
  step runs locally and is free.

All commands below run from this `homework_2/` folder, with your Python
environment active.

---

## 1. Direct setup (recommended)

Everything is set up for you — three commands and you can chat with the agent:

```bash
pip install -r requirements.txt    # install dependencies
cp .env_example .env               # then edit .env: set ANTHROPIC_API_KEY=sk-ant-...
bash setup.sh                      # start DB + migrate + build index + index samples
```

`setup.sh` starts PostgreSQL (Docker), applies the migrations, builds the HNSW
similarity index, and indexes the sample invoices/contracts — so RAG is ready.

Then go to **[Interacting with the agent](#interacting-with-the-agent)**.

> The first run downloads the embedding model (~470 MB) once.

---

## 2. Step-by-step (optional)

Use this to verify the project from a clean slate and run the test suite.

**Reset first (start from nothing):**

```bash
docker compose down -v     # remove the database container + all its data
```

**Then run each step:**

1. **Install dependencies**
   ```bash
   pip install -r requirements.txt
   ```
   > LangChain + Anthropic, document loaders, SQLAlchemy + pgvector + Alembic,
   > sentence-transformers (pulls in `torch`, which is large).

2. **Configure secrets**
   ```bash
   cp .env_example .env     # then set ANTHROPIC_API_KEY in .env
   ```
   `.env` already contains the database settings (`DATABASE_URL`, `POSTGRES_*`).

3. **Start the database**
   ```bash
   docker compose up -d --wait
   ```
   > Starts PostgreSQL with pgvector and waits until healthy. Check: `docker compose ps`.

4. **Create the tables (migrations)**
   ```bash
   alembic upgrade head
   ```
   > Enables the `vector` extension and creates `documents` + `document_chunks`.
   > Verify: `alembic current` → `0002_document_chunks (head)`.

5. **Build the HNSW index** (optional)
   ```bash
   python -m db.create_index
   ```

6. **Run the tests**
   ```bash
   pytest -q
   ```
   > Expect `58 passed`. Pure tests need nothing; database/RAG tests run real CRUD
   > and similarity search, and **skip automatically** if the database is down.

7. **Index the sample documents**
   ```bash
   python3 -c "from pathlib import Path; from rag import index_documents; index_documents(sorted(str(p) for p in Path('samples').glob('*.txt')))"
   ```
   > Loads, chunks, embeds, and stores each file (Document + chunks), with a progress
   > bar. Idempotent — running it again does not duplicate.

8. **(Optional) Try extraction → JSON**
   ```bash
   python3 -c "from extraction import extract_document; inv = extract_document('samples/factura_001.txt','factura'); print(inv.numar, inv.total, inv.furnizor)"
   ```
   > Prints `FV-2024-001 18088.0 SC TechPro Solutions SRL` and writes
   > `extracted_data/factura/FV-2024-001.json` (the folder is created automatically).

Then go to **[Interacting with the agent](#interacting-with-the-agent)**.

---

## Interacting with the agent

Start the interactive console:

```bash
python agent.py
```

Type questions, for example:

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

## Inspect the database

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
├── setup.sh                 # one-shot setup (DB + migrate + index + samples)
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
