'''
Tests for the db/ layer (Document model + DocumentRepository).

Two tiers:
  - Pure tests (no DB): model shape + domain exceptions + repository contract.
  - Integration tests: real CRUD against Postgres, auto-skipped if the DB is not
    reachable (so the suite still passes without Docker running). They use a
    rolled-back session for isolation — nothing is persisted.

Bring the DB up with:  docker compose up -d  &&  alembic upgrade head
'''

import pytest
from sqlalchemy import text

from db import (
    Document,
    DocumentNotFoundError,
    DocumentRepository,
    DuplicateDocumentError,
    InvalidMetadataError,
    SessionLocal,
    engine,
)


def _db_available() -> bool:
    '''True only if we can connect AND the documents table exists (migrated).'''
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1 FROM documents LIMIT 1"))
        return True
    except Exception:
        return False


DB_AVAILABLE = _db_available()
requires_db = pytest.mark.skipif(
    not DB_AVAILABLE,
    reason="Postgres not reachable / not migrated (run: docker compose up -d && alembic upgrade head)",
)


# --------------------------------------------------------------------------- #
# Pure tests — no database needed                                             #
# --------------------------------------------------------------------------- #
def test_document_table_and_metadata_column():
    assert Document.__tablename__ == "documents"
    # doc_metadata attribute maps to the reserved DB column name "metadata".
    assert Document.__table__.c.metadata.name == "metadata"
    assert {"id", "filename", "content", "metadata", "created_at"} <= set(
        Document.__table__.c.keys()
    )


def test_domain_exceptions():
    assert isinstance(DocumentNotFoundError(7), Exception)
    assert "id=7" in str(DocumentNotFoundError(7))
    assert "a.pdf" in str(DuplicateDocumentError("a.pdf"))
    assert "must be a dict" in str(InvalidMetadataError("metadata must be a dict"))


def test_repository_update_whitelist():
    assert DocumentRepository._UPDATABLE == {"filename", "content", "doc_metadata"}


# --------------------------------------------------------------------------- #
# Integration tests — require a live, migrated Postgres                       #
# --------------------------------------------------------------------------- #
@pytest.fixture
def db():
    '''A session that is rolled back after each test (no data persists).'''
    session = SessionLocal()
    try:
        yield session
    finally:
        session.rollback()
        session.close()


@requires_db
def test_create_and_get(db):
    repo = DocumentRepository(db)
    # Unique test filename so get_by_filename never collides with real/demo data.
    name = "zz_test_create_and_get.txt"
    doc = repo.create(name, "FACTURA ...", {"doc_type": "factura"})
    assert doc.id is not None
    assert repo.get_by_id(doc.id).filename == name
    assert repo.get_by_filename(name).id == doc.id


@requires_db
def test_count_and_pagination(db):
    repo = DocumentRepository(db)
    before = repo.count()
    repo.create_batch(
        [
            {"filename": f"d{i}.txt", "content": "x", "doc_metadata": {}}
            for i in range(3)
        ]
    )
    assert repo.count() == before + 3
    page = repo.get_all(skip=0, limit=2)
    assert len(page) == 2  # ordered by created_at desc


@requires_db
def test_filter_by_metadata(db):
    repo = DocumentRepository(db)
    repo.create("c1.txt", "x", {"doc_type": "contract"})
    repo.create("f1.txt", "x", {"doc_type": "factura"})
    contracts = repo.filter_by_metadata("doc_type", "contract")
    assert all(d.doc_metadata["doc_type"] == "contract" for d in contracts)
    assert any(d.filename == "c1.txt" for d in contracts)


@requires_db
def test_update_and_update_metadata_merge(db):
    repo = DocumentRepository(db)
    doc = repo.create("u.txt", "old", {"doc_type": "factura"})
    repo.update(doc.id, content="new")
    assert repo.get_by_id(doc.id).content == "new"
    # JSONB || merge keeps existing keys and adds/overrides new ones.
    repo.update_metadata(doc.id, {"total": 18088})
    merged = repo.get_by_id(doc.id).doc_metadata
    assert merged["doc_type"] == "factura" and merged["total"] == 18088


@requires_db
def test_delete_and_delete_batch(db):
    repo = DocumentRepository(db)
    a = repo.create("a.txt", "x", {})
    b = repo.create("b.txt", "x", {})
    assert repo.delete(a.id) is True
    assert repo.get_by_id(a.id) is None
    assert repo.delete_batch([b.id]) == 1


@requires_db
def test_safe_methods_raise(db):
    repo = DocumentRepository(db)
    with pytest.raises(DocumentNotFoundError):
        repo.get_by_id_safe(10_000_000)
    repo.create_safe("dup.txt", "x", {})
    with pytest.raises(DuplicateDocumentError):
        repo.create_safe("dup.txt", "x", {})
    with pytest.raises(InvalidMetadataError):
        repo.create_safe("bad.txt", "x", metadata="not-a-dict")  # type: ignore[arg-type]
