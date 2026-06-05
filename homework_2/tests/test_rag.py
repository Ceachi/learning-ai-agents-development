'''
Tests for the RAG layer: RAGService + index_document.

  - Pure tests: config + get_context() logic (search monkeypatched, so no model
    download and no DB).
  - Integration test: real embed → index_document → semantic search, gated on both
    Postgres availability and sentence-transformers being importable. Indexing is
    done without doc_type, so it makes no LLM call.
'''

from types import SimpleNamespace

import pytest
from sqlalchemy import text

from db import DocumentRepository, engine, transaction
from rag import DEFAULT_THRESHOLD, MODEL_NAME, RAGService, index_document


def _db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM document_chunks LIMIT 1"))
        return True
    except Exception:
        return False


def _model_available() -> bool:
    try:
        import sentence_transformers  # noqa: F401

        return True
    except Exception:
        return False


requires_rag = pytest.mark.skipif(
    not (_db_available() and _model_available()),
    reason="needs Postgres + sentence-transformers (docker compose up -d && pip install sentence-transformers)",
)


# --------------------------------------------------------------------------- #
# Pure tests — no model, no database                                          #
# --------------------------------------------------------------------------- #
def test_rag_config():
    assert MODEL_NAME == "paraphrase-multilingual-MiniLM-L12-v2"
    assert DEFAULT_THRESHOLD == 0.4


def test_get_context_empty(monkeypatch):
    svc = RAGService(db=None)
    monkeypatch.setattr(svc, "search", lambda query, top_k=5: [])
    assert svc.get_context("anything") == ""


def test_get_context_formats_and_filters_by_threshold(monkeypatch):
    svc = RAGService(db=None)
    near = SimpleNamespace(
        content="Clauza reziliere: 30 zile",
        document=SimpleNamespace(filename="contract.txt"),
    )
    far = SimpleNamespace(
        content="irrelevant",
        document=SimpleNamespace(filename="x.txt"),
    )
    monkeypatch.setattr(svc, "search", lambda query, top_k=5: [(near, 0.9), (far, 0.1)])
    ctx = svc.get_context("reziliere", threshold=0.4)
    assert "[contract.txt] Clauza reziliere: 30 zile" in ctx
    assert "irrelevant" not in ctx  # below threshold → filtered out


# --------------------------------------------------------------------------- #
# Integration test — real embeddings + Postgres                               #
# --------------------------------------------------------------------------- #
@requires_rag
def test_index_and_search_real(tmp_path):
    doc_path = tmp_path / "contract_rag_test.txt"
    doc_path.write_text(
        "Clauza 5.3: Rezilierea contractului se face cu preaviz de 30 de zile.\n\n"
        "Clauza 7.1: Penalitatile pentru intarziere sunt de 0.1% pe zi.",
        encoding="utf-8",
    )
    try:
        document = index_document(str(doc_path))  # no doc_type → no LLM call
        assert document.id is not None

        # Global search; scope results to the document we just indexed so the
        # assertion is robust to anything else already stored.
        with transaction() as db:
            results = RAGService(db).search("Cum functioneaza rezilierea?", top_k=10)
        own = [(c, s) for c, s in results if c.document_id == document.id]
        assert own, "the indexed document should be retrievable"
        top_chunk, top_score = own[0]
        assert "rezilier" in top_chunk.content.lower()
        # Clearly above orthogonal noise (~0); exact value is model-dependent.
        assert top_score > 0.2
        assert top_chunk.document.filename == "contract_rag_test.txt"
    finally:
        # Clean up (index_document commits) — cascade removes its chunks.
        with transaction() as db:
            repo = DocumentRepository(db)
            existing = repo.get_by_filename("contract_rag_test.txt")
            if existing is not None:
                repo.delete(existing.id)
