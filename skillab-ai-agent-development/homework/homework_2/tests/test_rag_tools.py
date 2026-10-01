'''
Tests for the search_documents agent tool.

  - Pure: the tool is registered and exposed in the catalog with a useful docstring.
  - Integration: index a temp document, then call the tool through ToolWrapper and
    assert it returns the relevant excerpt with its source. Gated on Postgres +
    sentence-transformers; cleans up after itself.
'''

import pytest
from sqlalchemy import text

from db import DocumentRepository, engine, transaction
from rag import index_document
from tools import ToolWrapper
from tools.registry import TOOL_REGISTRY


def _rag_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM document_chunks LIMIT 1"))
        import sentence_transformers  # noqa: F401

        return True
    except Exception:
        return False


requires_rag = pytest.mark.skipif(
    not _rag_available(),
    reason="needs Postgres + sentence-transformers",
)


# --------------------------------------------------------------------------- #
# Pure tests                                                                   #
# --------------------------------------------------------------------------- #
def test_search_documents_registered():
    assert "search_documents" in TOOL_REGISTRY
    assert len(TOOL_REGISTRY["search_documents"]["description"]) >= 15


def test_search_documents_in_catalog():
    names = {t["name"] for t in ToolWrapper.catalog("anthropic")}
    assert "search_documents" in names


# --------------------------------------------------------------------------- #
# Integration test                                                            #
# --------------------------------------------------------------------------- #
@requires_rag
def test_search_documents_returns_cited_context(tmp_path):
    doc_path = tmp_path / "zz_tool_contract.txt"
    doc_path.write_text(
        "Clauza 5.3: Rezilierea contractului se face cu preaviz de 30 de zile.",
        encoding="utf-8",
    )
    try:
        index_document(str(doc_path))  # no doc_type → no LLM call
        result = ToolWrapper.call("search_documents", {"query": "Ce clauze de reziliere avem?"})
        assert "zz_tool_contract.txt" in result   # source is cited
        assert "rezilier" in result.lower()       # relevant content retrieved
    finally:
        with transaction() as db:
            repo = DocumentRepository(db)
            existing = repo.get_by_filename("zz_tool_contract.txt")
            if existing is not None:
                repo.delete(existing.id)
