'''
Tests for DocumentChunk + ChunkRepository.

Embeddings here are synthetic 384-dim unit vectors, so similarity_search is
deterministic without loading sentence-transformers: a unit vector at position i
has cosine similarity 1.0 with itself and 0.0 with a unit vector at a different
position.

Integration tests auto-skip if Postgres (with the document_chunks table) is not
reachable. Bring it up with: docker compose up -d && alembic upgrade head
'''

import pytest
from sqlalchemy import text

from db import (
    ChunkRepository,
    DocumentChunk,
    DocumentRepository,
    SessionLocal,
    engine,
)
from db.models import EMBEDDING_DIM


def _db_available() -> bool:
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM document_chunks LIMIT 1"))
        return True
    except Exception:
        return False


requires_db = pytest.mark.skipif(
    not _db_available(),
    reason="Postgres/document_chunks not reachable (docker compose up -d && alembic upgrade head)",
)


def _unit_vec(pos: int, dim: int = EMBEDDING_DIM) -> list[float]:
    '''A unit vector with 1.0 at `pos` — handy for deterministic cosine tests.'''
    v = [0.0] * dim
    v[pos] = 1.0
    return v


# --------------------------------------------------------------------------- #
# Pure tests — no database                                                    #
# --------------------------------------------------------------------------- #
def test_chunk_table_and_columns():
    assert DocumentChunk.__tablename__ == "document_chunks"
    assert {"id", "document_id", "content", "chunk_index", "embedding"} <= set(
        DocumentChunk.__table__.c.keys()
    )
    assert EMBEDDING_DIM == 384


def test_chunk_has_unique_constraint_and_cascade_fk():
    fk = list(DocumentChunk.__table__.c.document_id.foreign_keys)[0]
    assert fk.ondelete == "CASCADE"
    constraint_names = {c.name for c in DocumentChunk.__table__.constraints}
    assert "uq_doc_chunk_idx" in constraint_names


# --------------------------------------------------------------------------- #
# Integration tests — require a live, migrated Postgres                       #
# --------------------------------------------------------------------------- #
@pytest.fixture
def db():
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@requires_db
def test_create_and_get_document_chunks(db):
    drepo, crepo = DocumentRepository(db), ChunkRepository(db)
    doc = drepo.create("chunks.txt", "full text", {})
    crepo.create_chunks_batch(
        [
            {"document_id": doc.id, "content": "c0", "chunk_index": 0, "embedding": _unit_vec(0)},
            {"document_id": doc.id, "content": "c1", "chunk_index": 1, "embedding": _unit_vec(1)},
        ]
    )
    chunks = crepo.get_document_chunks(doc.id)
    assert [c.chunk_index for c in chunks] == [0, 1]  # ordered by chunk_index
    assert crepo.get_chunk_by_id(chunks[0].id).content == "c0"


@requires_db
def test_similarity_search_ranks_nearest(db):
    drepo, crepo = DocumentRepository(db), ChunkRepository(db)
    doc = drepo.create("zz_test_sim.txt", "x", {})
    crepo.create_chunks_batch(
        [
            {"document_id": doc.id, "content": "chunk A", "chunk_index": 0, "embedding": _unit_vec(0)},
            {"document_id": doc.id, "content": "chunk B", "chunk_index": 1, "embedding": _unit_vec(1)},
        ]
    )
    # similarity_search is global (across all documents). A unit vector identical
    # to the query has cosine 1.0 — the global maximum — so chunk A must rank #1
    # regardless of any other data already in the table.
    results = crepo.similarity_search(_unit_vec(0), top_k=100)
    assert results[0][0].content == "chunk A"
    assert results[0][1] > 0.99
    assert results[0][0].document.filename == "zz_test_sim.txt"  # joinedload works
    # Among THIS document's chunks, A (≈1.0) ranks above B (≈0.0).
    own = {c.content: s for c, s in results if c.document_id == doc.id}
    assert own["chunk A"] > own["chunk B"]


@requires_db
def test_search_with_threshold_filters(db):
    drepo, crepo = DocumentRepository(db), ChunkRepository(db)
    doc = drepo.create("zz_test_thr.txt", "x", {})
    crepo.create_chunks_batch(
        [
            {"document_id": doc.id, "content": "near", "chunk_index": 0, "embedding": _unit_vec(0)},
            {"document_id": doc.id, "content": "far", "chunk_index": 1, "embedding": _unit_vec(5)},
        ]
    )
    hits = crepo.search_with_threshold(_unit_vec(0), min_score=0.5, top_k=100)
    # Scope to this document's chunks: "near" (≈1.0) kept, "far" (≈0.0) filtered out.
    own = [c.content for c, _ in hits if c.document_id == doc.id]
    assert own == ["near"]


@requires_db
def test_cascade_delete_removes_chunks(db):
    drepo, crepo = DocumentRepository(db), ChunkRepository(db)
    doc = drepo.create("casc.txt", "x", {})
    crepo.create_chunk(doc.id, "only chunk", 0, _unit_vec(2))
    assert len(crepo.get_document_chunks(doc.id)) == 1
    drepo.delete(doc.id)                 # DB-level ON DELETE CASCADE
    assert crepo.get_document_chunks(doc.id) == []
