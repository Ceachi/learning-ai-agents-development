# Document Analyst

Sistem multi-agent care răspunde la întrebări despre **achiziții publice (SEAP)**, combinând două căi:

- **RAG** — caută semantic în documente (pgvector) și răspunde din context.
- **NL2SQL** — traduce întrebări în SQL peste tabele structurate (achiziții directe, anunțuri de inițiere) și analizează datele.

Construit cu **Python**, **LangChain** și **LangGraph**, provider-agnostic (Ollama / Gemini / Anthropic).

> Proiect de referință pentru cursul **AI Agent Development** (Skillab). Codul e organizat pe **capabilități**, nu pe lecții. Pentru maparea temelor în proiect, vezi [De unde vine fiecare piesă](#de-unde-vine-fiecare-piesă).

---

## Cuprins

- [Ce face](#ce-face)
- [Arhitectură](#arhitectură)
- [Structura proiectului](#structura-proiectului)
- [Cei doi agenți principali](#cei-doi-agenți-principali)
- [Frontend](#frontend)
- [De unde vine fiecare piesă](#de-unde-vine-fiecare-piesă)
- [Setup](#setup)
- [Populare bază de date](#populare-bază-de-date)
- [Utilizare](#utilizare)
- [Tech stack](#tech-stack)

---

## Ce face

- **Chat conversațional** cu memory în sesiune și persistență opțională în DB.
- **3 moduri de operare**: Chat (LLM direct), RAG (documente), SQL (bază de date).
- **Frontend React** cu sidebar pentru configurare în timp real.
- **Provider-agnostic**: Ollama (local), Anthropic, Google Gemini.
- **RAG** cu Orchestrator care evaluează și re-caută dacă răspunsul nu e suficient.
- **NL2SQL** cu validare anti-injection, execuție și retry automat.
- **Analyst** multi-step: planifică query-uri + tools peste mai multe tabele.
- **LLM Caching**: Anthropic prompt caching cu TTL 1h pentru cost/latency redus.
- **Optimizări**: intent classifier (rutare fără LLM), semantic cache.
- **Guardrails**: validare input + detecție prompt injection (regex + LLM).
- **MCP server**: agenții expuși ca tools pentru Claude Code.

---

## Arhitectură

Un **router** decide, pe baza intenției, ce cale rezolvă întrebarea:

```
                              ┌─────────────┐
                user ────────►│  ChatSession│
                              └──────┬──────┘
                                     │
                              ┌──────▼───────┐
                              │  Guardrails  │  validare + prompt injection
                              └──────┬───────┘
                                     │
                          ┌──────────▼──────────┐
                          │  Intent Classifier  │  chat / rag / sql
                          └───┬───────┬─────┬───┘
                              │       │     │
               „conversație"  │       │     │  „date / numere"
                       ┌──────▼──┐    │   ┌─▼─────────┐
                       │  Chat   │    │   │  Analyst  │
                       │ (LLM)   │    │   │  (NL2SQL) │
                       └─────────┘    │   └─────┬─────┘
                                      │         │
                          „documente" │    ┌────▼──────┐
                              ┌───────▼──┐ │NL2SQLAgent│
                              │Orchestr. │ └─────┬─────┘
                              │  (RAG)   │       │
                              └────┬─────┘       │
                                   │             │
                              ┌────▼─────┐       │
                              │ RAGAgent │       │
                              └────┬─────┘       │
                                   │             │
                              ┌────▼─────────────▼────┐
                              │  PostgreSQL + pgvector │
                              │   chunks + tabele SEAP │
                              └───────────────────────┘
```

Fiecare agent e un **graf LangGraph** independent cu state tipat (Pydantic), noduri, conditional edges și retry/fallback.

---

## Structura proiectului

Un singur nivel de module, fiecare cu o responsabilitate clară. Fără librărie externă — tot ce era reutilizabil (`llm`, `prompts`, `tools`) e direct în proiect.

```
document-analyst/
│
├── README.md
├── BUILD_PLAN.md             # ordinea de construcție, componentă cu componentă
├── pyproject.toml
├── .env.example              # provider LLM + DATABASE_URL
├── docker-compose.yml        # PostgreSQL + pgvector
│
├── app/
│   ├── main.py               # entrypoint: chat / rulare agenți
│   ├── chat.py               # interfața Q&A cu istoric, memory, settings
│   ├── config.py             # configurare din environment
│   │
│   ├── api/                  # FastAPI endpoints
│   │   ├── main.py           # app factory
│   │   ├── routes.py         # /chat, /config endpoints
│   │   └── schemas.py        # Pydantic models pentru API
│   │
│   ├── llm/                  # abstracție provider (Ollama / Gemini / Anthropic)
│   │   ├── base.py           # LLMProvider: generate_sync, model, streaming
│   │   └── factory.py        # get_llm(provider, model)
│   │
│   ├── prompts/              # PromptRegistry + template Jinja2 din YAML
│   │   ├── registry.py
│   │   ├── template.py
│   │   └── library/          # *.yaml (analyst_plan, nl2sql_error, rag_evaluate...)
│   │
│   ├── tools/                # tools cu Pydantic + @register_tool
│   │   ├── registry.py       # ToolWrapper: register, call, to_prompt_string
│   │   └── data_tools.py     # join_data, filter_data
│   │
│   ├── agents/               # cei 4 agenți LangGraph
│   │   ├── state.py          # toate state-urile Pydantic într-un loc
│   │   ├── router.py         # intent classifier (rag/sql/chat)
│   │   ├── rag.py            # refine → search (pgvector)
│   │   ├── orchestrator.py   # call_rag → evaluate → answer (loop)
│   │   ├── nl2sql.py         # context → generate → validate → execute → retry
│   │   └── analyst.py        # make_plan → execute_step(loop) → synthesize
│   │
│   ├── db/                   # stratul de date
│   │   ├── database.py       # engine + transaction() context manager
│   │   ├── models.py         # SQLAlchemy: DocumentChunk, AchizitieDirecta, AnuntInitiere
│   │   └── repositories.py   # repository pattern (data access)
│   │
│   ├── rag/                  # serviciul de embedding + căutare
│   │   └── service.py        # RAGService: embed, add_chunk(s), search
│   │
│   ├── ingest/               # populare bază de date
│   │   ├── documents.py      # load → chunk → embed → store
│   │   └── tabular.py        # CSV achiziții/anunțuri → tabele
│   │
│   ├── optimize/             # optimizări fără-LLM și de cost (L7-L8)
│   │   ├── intent_classifier.py  # TF-IDF + LogisticRegression
│   │   ├── memory.py             # conversation memory (persistată în Postgres)
│   │   └── cache.py              # prompt / semantic caching
│   │
│   ├── guardrails/           # securitate (L9)
│   │   ├── input_validation.py
│   │   └── prompt_injection.py
│   │
│   └── mcp/                  # server MCP (L10)
│       └── server.py         # expune Orchestrator + Analyst ca tools
│
├── data/                     # documente + CSV-uri + scheme JSON tabele
│   ├── documents/            # .docx files pentru RAG
│   ├── schemas/              # JSON schemas pentru tabele SQL
│   └── rag_demo.dump         # PostgreSQL dump cu date demo
│
├── frontend/                 # React frontend
│   ├── src/
│   │   ├── components/       # ChatContainer, Sidebar, MessageBubble...
│   │   ├── hooks/            # useChat, useSettings
│   │   └── types/            # TypeScript interfaces
│   └── vite.config.ts
│
└── tests/
```

---

## Cei doi agenți principali

### Calea RAG — `Orchestrator` + `RAGAgent`

Orchestratorul nu caută singur: deleagă către RAGAgent, **evaluează** dacă chunk-urile găsite sunt suficiente și, dacă nu, trimite feedback și re-caută (cu query rafinat), până la `max_iterations`.

```
Orchestrator:  call_rag → evaluate ──can_answer?──► answer → END
                  ▲                  │ nu
                  └──────────────────┘
RAGAgent:      refine → search(pgvector) → END
```

### Calea SQL — `Analyst` + `NL2SQLAgent`

Analystul face un **plan** cu pași identificați prin ID (`q1`, `q2`, `joined`...): query-uri pe tabele (via NL2SQL) și tools de procesare (`join_data`, `filter_data`). Rezultatele se acumulează în `slices[step_id]`. La final, sintetizează răspunsul.

```
Analyst:    make_plan → execute_step (loop pe plan) → synthesize → END
NL2SQL:     get_context → generate → validate → execute → END
                                        │           │
                                        └─ handle_error (retry ×N) ─┘
```

---

## Frontend

Interfață React cu un **sidebar de configurare** care permite ajustarea parametrilor în timp real:

```
┌─────────────────────────────────────────────────┐
│  SIDEBAR (320px)  │      CHAT (flex: 1)         │
│                   │                              │
│  ┌─────────────┐  │  ┌────────────────────────┐ │
│  │ LLM Config  │  │  │ Chat Header            │ │
│  │ Provider ▼  │  │  ├────────────────────────┤ │
│  │ Model ▼     │  │  │                        │ │
│  │ Temp ═══○   │  │  │ Messages + Metrics     │ │
│  ├─────────────┤  │  │                        │ │
│  │ FEATURES    │  │  │ [CACHED] 1200 tokens   │ │
│  │ Intent ▼    │  │  │         ⚡ 1668 cached │ │
│  │ ☑ Guardrails│  │  ├────────────────────────┤ │
│  │ ☑ Memory    │  │  │ Input Bar              │ │
│  │ ☐ Persist DB│  │  └────────────────────────┘ │
│  ├─────────────┤  │                              │
│  │ LLM Caching │  │                              │
│  │ ☐ Enabled   │  │                              │
│  ├─────────────┤  │                              │
│  │ ▼ Advanced  │  │                              │
│  └─────────────┘  │                              │
└─────────────────────────────────────────────────┘
```

### Opțiuni configurabile

| Opțiune | Tip | Default | Descriere |
|---------|-----|---------|-----------|
| `llm_provider` | dropdown | ollama | anthropic, google, ollama |
| `llm_model` | dropdown | per provider | Model specific providerului |
| `llm_temperature` | slider | 0.0 | Creativitate (0.0 - 1.0) |
| `use_guardrails` | toggle | true | Validare input + prompt injection |
| `memory_enabled` | toggle | true | Conversație cu context în sesiune |
| `persist_memory` | toggle | false | Salvare conversație în DB |
| `intent` | dropdown | auto | Auto / Chat / RAG / SQL |
| `rag_top_k` | number | 5 | Chunks de returnat |
| `rag_threshold` | slider | 0.3 | Similarity threshold |
| `cache_enabled` | toggle | true | Semantic cache |
| `llm_caching_enabled` | toggle | false | Anthropic prompt caching |
| `llm_caching_context` | textarea | - | System context pentru cache |

Setările se păstrează în `localStorage` și sunt trimise la fiecare request.

---

## De unde vine fiecare piesă

Temele cursului (L2→L10, cumulative) se regăsesc în proiect astfel:

| Temă | Subiect | Module în proiect |
|------|---------|-------------------|
| **L1** | Chat Q&A + provider-agnostic | `app/chat.py`, `app/llm/` |
| **L2** | Tools (Pydantic) + Prompts (YAML/Jinja2) | `app/tools/`, `app/prompts/` |
| **L4** | Extracție + RAG + pgvector | `app/ingest/`, `app/rag/`, `app/db/` |
| **L6** | LangGraph (state, noduri, edges) + Multi-agent | `app/agents/` (toți cei 4 agenți) |
| **L8** | Memory + Caching + Intent Classifier | `app/optimize/` |
| **L10** | MCP server + Guardrails | `app/mcp/`, `app/guardrails/` |

> Temele sunt date la fiecare două lecții și **fiecare se construiește peste cea anterioară**. De aceea proiectul final le conține pe toate, integrate ca un sistem unic — exact ce vede un student la final.

---

## Setup

### Opțiunea 1: Docker Development (recomandat)

```bash
git clone <repo-url>
cd document-analyst

cp .env.example .env                 # configurează API keys

# Pornește totul (PostgreSQL + Backend + Frontend)
docker compose -f docker-compose.dev.yml up --build
```

Servicii disponibile:
- **Frontend**: http://localhost:5173
- **Backend API**: http://localhost:8000
- **PostgreSQL**: localhost:5432

### Opțiunea 2: Local Development

```bash
git clone <repo-url>
cd document-analyst

docker-compose up -d                 # PostgreSQL + pgvector

python -m venv .venv && source .venv/bin/activate
pip install -e .

cp .env.example .env                 # alege provider + setează DATABASE_URL
```

`.env` — alege un provider LLM:

| Provider | Cost | Bun pentru |
|----------|------|------------|
| Ollama | gratis (local) | dezvoltare (necesită 8GB+ RAM) |
| Gemini | free tier | proiecte mici |
| Anthropic | plătit | calitate de producție |

---

## Populare bază de date

### Opțiunea 1: Restore dump (rapid, include embeddings)

**1. Descarcă dump-ul:**

[⬇️ Download rag_demo.dump](https://drive.google.com/file/d/1ZW8C60-R9S_H6nL6aq0CMYXeaJ5m4oLX/view?usp=sharing)

Salvează fișierul în `data/rag_demo.dump`.

**2. Restore în PostgreSQL:**

```bash
# Cu Docker
docker compose -f docker-compose.dev.yml exec postgres pg_restore \
  -U analyst -d document_analyst --clean --if-exists \
  /data/rag_demo.dump

# Local
pg_restore -U analyst -d document_analyst --clean --if-exists data/rag_demo.dump
```

### Opțiunea 2: Ingest manual

**Documente (RAG)** — încarcă, chunk-uiește, embeddează și stochează în pgvector:

```bash
# Docker
docker compose -f docker-compose.dev.yml exec backend \
  python -m app.ingest.documents data/documents/

# Local
python -m app.ingest.documents data/documents/
```

**Tabele SQL** — încarcă CSV-uri în tabelele `achizitii_directe` și `anunturi_initiere`:

```bash
# Docker
docker compose -f docker-compose.dev.yml exec backend \
  python -m app.ingest.tabular achizitii data/achizitii.csv

# Local
python -m app.ingest.tabular achizitii data/achizitii.csv
python -m app.ingest.tabular anunturi data/anunturi.csv
```

### Migrații Alembic

```bash
# Docker
docker compose -f docker-compose.dev.yml exec backend alembic upgrade head

# Local
alembic upgrade head
```

---

## Utilizare

```bash
# Chat interactiv (routerul alege RAG sau SQL)
python -m app.main

# Pornește serverul MCP
python -m app.mcp.server

# API server (pentru frontend)
uvicorn app.api.main:app --reload --port 8000
```

---

## Tech stack

| Categorie | Tool |
|-----------|------|
| Limbaj | Python 3.x |
| Framework agenți | LangChain, LangGraph |
| LLM | provider-agnostic (Ollama / Gemini / Anthropic) |
| Bază de date | PostgreSQL + pgvector |
| Embeddings | sentence-transformers (all-MiniLM-L6-v2, 384d) |
| ML | scikit-learn (intent classifier) |
| Prompts | YAML + Jinja2 |
| Protocol | MCP (Model Context Protocol) |
| Frontend | React + TypeScript + Vite |
| API | FastAPI |
| Deployment | Docker Compose |

---

*Proiect de referință — AI Agent Development, Skillab.*
