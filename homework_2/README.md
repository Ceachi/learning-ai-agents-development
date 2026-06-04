# Document Analyst Agent — Extraction Pipeline + Tools + ReAct

Homework 2 (Document Analyst cu RAG). Builds on the Lesson 1–2 QA agent by adding
the **Lesson 3 document-extraction pipeline** (`Load → Chunk → Extract → Save`) and
wrapping it as agent tools, so the same ReAct agent can now extract structured data
from invoices and contracts.

> **Scope of this homework.** The full assignment (hw4) has 4 parts. Implemented
> here is **Part 1 — Extraction Pipeline (L3)**. Parts 2–4 (PostgreSQL + pgvector,
> RAG with embeddings, RAG-as-tool) are Lesson 4 and will be added later.

## Features

- **Document extraction pipeline (L3)** — `Load → Chunk → Extract → Save`:
  - a **loader registry** over file extension (PDF / DOCX / TXT / CSV);
  - **chunking** with `RecursiveCharacterTextSplitter`, applied only when a
    document is large (> ~4K chars);
  - **structured extraction** into Pydantic schemas (`Invoice`, `Contract`) via
    LangChain `with_structured_output`;
  - **organized JSON output** under `extracted_data/<type>/<numar>.json`.
- **Tools with Pydantic** — each tool declares its parameters as a Pydantic
  `BaseModel`; a `@register_tool` decorator validates and auto-registers them.
- **Prompts as configuration** — prompts live in versioned YAML files, rendered
  with Jinja2, with an automatic variable contract.
- **ReAct agent** — the LLM requests tools, the app executes them, results flow
  back as observations until a final answer is produced.
- **Provider-agnostic** — an `LLMFactory` supports Anthropic, OpenAI, Google,
  and Ollama (default: Anthropic). The extraction pipeline reuses the same factory.

## Project structure

```
homework_2/
├── agent.py                 # LLMFactory, ReAct loop, entry points (ask/chat)
├── tools/
│   ├── params_models.py     # Pydantic BaseModel per basic tool
│   ├── registry.py          # TOOL_REGISTRY + @register_tool decorator
│   ├── basic_tools.py       # calculator, get_datetime, web_search
│   ├── extraction_tools.py  # extract_invoice_tool, extract_contract_tool
│   ├── tool_wrapper.py      # ToolWrapper.call() + catalog()
│   └── __init__.py          # exports ToolWrapper, auto-registers all tools
├── extraction/              # Lesson 3 pipeline: Load → Chunk → Extract → Save
│   ├── loaders.py           # LOADER_REGISTRY + load_document()
│   ├── schemas.py           # Product, Invoice, Contract (Pydantic)
│   ├── chunking.py          # should_chunk() + chunk_documents()
│   ├── storage.py           # save_json()
│   ├── pipeline.py          # ExtractionPipeline + EXTRACTION_REGISTRY + extract_document()
│   └── __init__.py          # public API
├── prompts/
│   ├── registry.py          # PromptTemplate, PromptRegistry, hot reload
│   ├── planner.yaml         # ReAct system prompt (the agent)
│   ├── analyst.yaml / summary.yaml / extract.yaml / reminder.yaml
├── samples/                 # test invoices/contracts (txt, csv)
├── extracted_data/          # generated JSON output (gitignored)
├── tests/                   # smoke tests (no LLM calls)
├── conftest.py              # pytest setup
└── requirements.txt
```

API keys live in `.env` in this folder (see `.env_example`).

## Setup

```bash
# from homework_2/
pip install -r requirements.txt

# configure your key: copy the template and add your key
cp .env_example .env
# then edit .env and set ANTHROPIC_API_KEY=...
```

## Usage

### Extract a document (programmatic)

```python
from extraction import extract_document

# Load → Chunk (if needed) → Extract → Save; returns a validated Pydantic object
invoice = extract_document("samples/factura_001.txt", "factura")
print(invoice.numar, invoice.total)        # FV-2024-001 18088.0
# -> saved to extracted_data/factura/FV-2024-001.json

contract = extract_document("samples/contract_servicii.txt", "contract")
print(contract.prestator, contract.durata_luni)
```

Use the pipeline directly for a custom schema:

```python
from extraction import ExtractionPipeline, Invoice
invoice = ExtractionPipeline().process("samples/factura_001.txt", Invoice)
```

### Through the agent (it picks the tool itself)

```python
from agent import ask

print(ask("Procesează factura din samples/factura_001.txt și spune-mi furnizorul și totalul."))
# The agent selects extract_invoice_tool, runs the pipeline, and reports the result.
```

The agent chooses `extract_invoice_tool` vs `extract_contract_tool` automatically
based on the tool **docstrings** — no manual if/else, no prompt change required.

### Interactive chat (console)

Run from `homework_2/`:

```bash
python agent.py
```

Multi-turn conversation; history is kept across turns and tool calls are shown
inline so you can watch Think → Act → Observe. Commands: `exit` / `quit`, `reset`.

## How extraction works

1. **Load** — `load_document(path)` looks up a loader by file extension in
   `LOADER_REGISTRY` and returns a uniform `list[Document]`. Unsupported types
   raise `ValueError`; a missing file raises `FileNotFoundError`.
2. **Chunk** — `should_chunk(docs)` is `True` only for large documents (> 4K
   chars); then `chunk_documents()` splits with `RecursiveCharacterTextSplitter`.
   Invoices are small, so they skip chunking.
3. **Extract** — `ExtractionPipeline.process(path, schema)` sends the text to the
   LLM via `llm.with_structured_output(schema)` and returns a validated object.
4. **Save** — `save_json()` writes `extracted_data/<doc_type>/<numar>.json`
   (`ensure_ascii=False`, so Romanian diacritics are preserved).

`EXTRACTION_REGISTRY` routes a `doc_type` ("factura" / "contract") to its schema
and chunk policy — a new document type is one dict entry.

> **Design note.** The L3 slides extract with Google Gemini (`genai.Client` +
> `response_schema`). This project keeps the exact L3 *structure* but performs the
> extract step with **LangChain + Anthropic** via the existing `LLMFactory` and
> `with_structured_output` — matching the hw4 flow box and reusing the L1–L2 agent
> (one provider, one key).

## Adding a tool

```python
# tools/extraction_tools.py (or basic_tools.py)
class MyToolParams(BaseModel):
    value: str = Field(description="...")

@register_tool
def my_tool(params: MyToolParams) -> dict:
    '''Clear description: what it does, when to use it, an example.'''
    ...
```

The decorator enforces a single `BaseModel` parameter and a meaningful docstring
(which becomes the description the LLM uses to decide when to call the tool).

## Testing

```bash
pytest -v
```

Smoke tests cover tool registration, the safe (AST-based) calculator, Pydantic
validation, prompt loading/rendering — and the extraction pipeline's load / chunk /
schema / save steps and tool registration — all **without making LLM calls**.

## Design patterns

- **Registry** — `TOOL_REGISTRY`, `PromptRegistry`, `LOADER_REGISTRY`, `EXTRACTION_REGISTRY`
- **Decorator** — `@register_tool`
- **Factory** — `LLMFactory`
- **Singleton** — `get_prompt_registry()` (via `lru_cache`)
- **Pipeline** — `ExtractionPipeline` (Load → Chunk → Extract → Save)
