'''
ExtractionPipeline + EXTRACTION_REGISTRY + extract_document — the full pipeline
(Lesson 3, §4): Load -> Chunk -> Extract -> Save.

Design note (see specs/README.md, Bloc B): the L3 slides extract with Google
Gemini (genai.Client + response_schema). We keep the exact L3 STRUCTURE but the
extract step uses LangChain + Anthropic via the existing LLMFactory and
llm.with_structured_output(schema) — exactly as the hw4.pdf flow shows
(`data = llm.with_structured_output(Invoice)`). One provider across the project.

The LLM client is lazy (created on first use), so the pipeline is safe to
instantiate without an API key and safe to reuse across processes.
'''

from typing import Type

from pydantic import BaseModel

from .chunking import chunk_documents, should_chunk
from .loaders import load_document
from .schemas import Contract, Invoice
from .storage import save_json


class ExtractionPipeline:
    '''
    Reusable extraction pipeline. One entry point — process(file_path, schema) —
    works for any document and any Pydantic schema.
    '''

    def __init__(
        self,
        provider: str | None = None,
        model: str | None = None,
        chunk_size: int = 2000,
        chunk_overlap: int = 200,
    ):
        self.provider = provider
        self.model = model
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self._llm = None  # lazy — the client is built on first use

    @property
    def llm(self):
        '''
        Build the tool-less LangChain LLM on first access.

        Imported lazily from agent.py to avoid a circular import
        (tools/__init__ -> extraction_tools -> pipeline -> agent -> tools).
        temperature=0 keeps extraction deterministic.
        '''
        if self._llm is None:
            from agent import DEFAULT_MODEL, DEFAULT_PROVIDER, LLMFactory

            self._llm = LLMFactory.create(
                self.provider or DEFAULT_PROVIDER,
                model=self.model or DEFAULT_MODEL,
                temperature=0,
            )
        return self._llm

    def process(self, file_path: str, schema: Type[BaseModel]) -> BaseModel:
        '''
        Run Load -> Chunk (if needed) -> Extract and return a validated object.

        For large documents we combine the first 3 chunks — in invoices and
        contracts the key info (number, parties, totals) sits at the start
        (L3, "Pipeline: Document Mare").
        '''
        # 1. Load
        docs = load_document(file_path)

        # 2. Chunk only if necessary
        if should_chunk(docs):
            chunks = chunk_documents(docs, self.chunk_size, self.chunk_overlap)
            text = "\n\n".join(c.page_content for c in chunks[:3])
        else:
            text = "\n\n".join(d.page_content for d in docs)

        # 3. Extract — Pydantic guarantees a validated, typed object (not a string)
        structured_llm = self.llm.with_structured_output(schema)
        return structured_llm.invoke(text)


# ---------------------------------------------------------------------------
# Routing by document type (L3 §4, slide46) — a new type is one dict entry.
# ---------------------------------------------------------------------------
EXTRACTION_REGISTRY: dict[str, dict] = {
    "factura": {"schema": Invoice, "chunk_size": None},    # invoices are small -> no chunking
    "contract": {"schema": Contract, "chunk_size": 2000},
}


def extract_document(file_path: str, doc_type: str, save: bool = True) -> BaseModel:
    '''
    High-level entry point: Load -> Chunk -> Extract -> (optional) Save.

    Looks up the schema + chunk policy in EXTRACTION_REGISTRY, runs the pipeline,
    saves the JSON under extracted_data/<doc_type>/, and returns the object.

    Raises KeyError for an unknown doc_type (caught and surfaced by the tool layer).
    '''
    if doc_type not in EXTRACTION_REGISTRY:
        raise KeyError(
            f"Unknown document type: '{doc_type}'. "
            f"Available: {', '.join(EXTRACTION_REGISTRY)}"
        )

    config = EXTRACTION_REGISTRY[doc_type]
    chunk_size = config["chunk_size"]

    # chunk_size=None means "don't chunk this type"; keep the default otherwise.
    pipeline = ExtractionPipeline(chunk_size=chunk_size or 2000)
    result = pipeline.process(file_path, config["schema"])

    if save:
        save_json(result, doc_type)

    return result
