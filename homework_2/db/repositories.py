'''
DocumentRepository — all Document DB logic in one place.

Repository pattern: encapsulation (the rest of the app never touches SQLAlchemy
directly), testability, and a single source of truth for queries.

Write methods flush() rather than commit() — the commit boundary is owned by the
transaction() context manager (db/database.py), so a multi-step unit of work
(e.g. a Document + its chunks) is atomic. Always use it as:

    with transaction() as db:
        repo = DocumentRepository(db)
        repo.create(...)
'''

from typing import Any

from sqlalchemy import delete as sql_delete
from sqlalchemy import func, select
from sqlalchemy import update as sql_update
from sqlalchemy.orm import Session, joinedload

from .exceptions import DocumentNotFoundError, DuplicateDocumentError, InvalidMetadataError
from .models import Document, DocumentChunk


class DocumentRepository:
    '''CRUD + metadata queries for Document, scoped to one Session.'''

    # Fields allowed in update() — guards against mass-assignment.
    _UPDATABLE = {"filename", "content", "doc_metadata"}

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- CREATE ----------------------------------------------------------- #
    def create(self, filename: str, content: str, metadata: dict[str, Any]) -> Document:
        doc = Document(filename=filename, content=content, doc_metadata=metadata)
        self.db.add(doc)
        self.db.flush()       # assigns the generated id; commit happens in transaction()
        self.db.refresh(doc)  # load server defaults (created_at)
        return doc

    def create_batch(self, documents: list[dict[str, Any]]) -> list[Document]:
        docs = [Document(**d) for d in documents]
        self.db.add_all(docs)  # a single batched INSERT, far faster than N add()
        self.db.flush()
        for doc in docs:
            self.db.refresh(doc)
        return docs

    # --- READ ------------------------------------------------------------- #
    def get_by_id(self, doc_id: int) -> Document | None:
        # Modern SQLAlchemy: Session.get() looks up directly by primary key.
        return self.db.get(Document, doc_id)

    def get_by_filename(self, filename: str) -> Document | None:
        return (
            self.db.query(Document).filter(Document.filename == filename).first()
        )

    def get_all(self, skip: int = 0, limit: int = 100) -> list[Document]:
        return (
            self.db.query(Document)
            .order_by(Document.created_at.desc())
            .offset(skip)
            .limit(limit)
            .all()
        )

    def count(self) -> int:
        return self.db.query(func.count(Document.id)).scalar()

    def filter_by_metadata(self, key: str, value: str) -> list[Document]:
        # PostgreSQL ->> operator: extract a JSONB field as text.
        return (
            self.db.query(Document)
            .filter(Document.doc_metadata[key].astext == value)
            .all()
        )

    # --- UPDATE ----------------------------------------------------------- #
    def update(self, doc_id: int, **fields: Any) -> Document | None:
        clean = {k: v for k, v in fields.items() if k in self._UPDATABLE}
        if not clean:
            return self.db.get(Document, doc_id)
        self.db.execute(
            sql_update(Document).where(Document.id == doc_id).values(**clean)
        )
        self.db.flush()
        return self.db.get(Document, doc_id)

    def update_metadata(self, doc_id: int, metadata: dict[str, Any]) -> Document | None:
        # JSONB merge at the DB level (atomic) — PostgreSQL's || operator.
        self.db.execute(
            sql_update(Document)
            .where(Document.id == doc_id)
            .values(doc_metadata=Document.doc_metadata.op("||")(metadata))
        )
        self.db.flush()
        doc = self.db.get(Document, doc_id)
        if doc is not None:
            self.db.refresh(doc)
        return doc

    # --- DELETE ----------------------------------------------------------- #
    def delete(self, doc_id: int) -> bool:
        result = self.db.execute(sql_delete(Document).where(Document.id == doc_id))
        self.db.flush()
        return result.rowcount > 0

    def delete_batch(self, doc_ids: list[int]) -> int:
        if not doc_ids:
            return 0
        result = self.db.execute(
            sql_delete(Document).where(Document.id.in_(doc_ids))
        )
        self.db.flush()
        return result.rowcount

    # --- SAFE variants (raise domain exceptions) -------------------------- #
    def get_by_id_safe(self, doc_id: int) -> Document:
        doc = self.db.get(Document, doc_id)
        if doc is None:
            raise DocumentNotFoundError(doc_id)
        return doc

    def create_safe(self, filename: str, content: str, metadata: dict[str, Any]) -> Document:
        if not isinstance(metadata, dict):
            raise InvalidMetadataError("metadata must be a dict")
        if self.get_by_filename(filename) is not None:
            raise DuplicateDocumentError(filename)
        return self.create(filename=filename, content=content, metadata=metadata)


class ChunkRepository:
    '''
    CRUD + vector similarity search for DocumentChunk.

    Like DocumentRepository, write methods flush() and leave the commit to the
    transaction() context manager, so a document and all its chunks are persisted
    atomically.
    '''

    def __init__(self, db: Session) -> None:
        self.db = db

    # --- WRITE ------------------------------------------------------------ #
    def create_chunk(
        self,
        document_id: int,
        content: str,
        chunk_index: int,
        embedding: list[float],
    ) -> DocumentChunk:
        chunk = DocumentChunk(
            document_id=document_id,
            content=content,
            chunk_index=chunk_index,
            embedding=embedding,
        )
        self.db.add(chunk)
        self.db.flush()
        self.db.refresh(chunk)
        return chunk

    def create_chunks_batch(self, chunks: list[dict]) -> list[DocumentChunk]:
        objs = [DocumentChunk(**c) for c in chunks]
        self.db.add_all(objs)  # single batched INSERT
        self.db.flush()
        for chunk in objs:
            self.db.refresh(chunk)
        return objs

    # --- READ ------------------------------------------------------------- #
    def get_document_chunks(self, document_id: int) -> list[DocumentChunk]:
        return (
            self.db.query(DocumentChunk)
            .filter(DocumentChunk.document_id == document_id)
            .order_by(DocumentChunk.chunk_index)
            .all()
        )

    def get_chunk_by_id(self, chunk_id: int) -> DocumentChunk | None:
        return self.db.get(DocumentChunk, chunk_id)

    # --- SEARCH (pgvector) ------------------------------------------------ #
    def similarity_search(
        self,
        query_embedding: list[float],
        top_k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        '''Top-k nearest chunks by cosine similarity.'''
        # 1 - (emb <=> q) → cosine distance converted to similarity in [0, 1].
        similarity = (
            1 - DocumentChunk.embedding.cosine_distance(query_embedding)
        ).label("score")
        stmt = (
            select(DocumentChunk, similarity)
            .options(joinedload(DocumentChunk.document))  # eager load — avoids N+1
            .order_by(DocumentChunk.embedding.cosine_distance(query_embedding))
            .limit(top_k)
        )
        rows = self.db.execute(stmt).all()
        return [(chunk, float(score)) for chunk, score in rows]

    def search_with_threshold(
        self,
        query_embedding: list[float],
        min_score: float = 0.4,
        top_k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        '''similarity_search filtered to results at or above min_score.'''
        results = self.similarity_search(query_embedding, top_k=top_k)
        return [(chunk, score) for chunk, score in results if score >= min_score]
