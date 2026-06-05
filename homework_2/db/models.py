'''
SQLAlchemy models.

Document — one row per ingested file. `doc_metadata` (JSONB) holds the structured
data extracted from the document (the Invoice/Contract model_dump() plus doc_type),
so it stays queryable via DocumentRepository.filter_by_metadata().

DocumentChunk — a chunk of a document plus its embedding, for similarity search.
A Document has many chunks (one-to-many, cascade delete).
'''

from sqlalchemy import (
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    UniqueConstraint,
    func,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.orm import relationship
from pgvector.sqlalchemy import Vector

from .database import Base

# Embedding dimensionality of the sentence-transformers model
# (paraphrase-multilingual-MiniLM-L12-v2 → 384). The pgvector column is fixed-size.
EMBEDDING_DIM = 384


class Document(Base):
    '''An ingested document: original file + full text + extracted metadata.'''

    __tablename__ = "documents"

    id = Column(Integer, primary_key=True, autoincrement=True)
    filename = Column(String(255), nullable=False, index=True)
    content = Column(Text, nullable=False)
    # "metadata" is reserved on SQLAlchemy's Declarative API → attribute renamed
    # to doc_metadata, while the DB column stays "metadata".
    doc_metadata = Column("metadata", JSONB, nullable=False, default=dict)
    created_at = Column(
        DateTime(timezone=True), server_default=func.now(), nullable=False
    )

    # One-to-many: deleting a Document deletes all its chunks.
    chunks = relationship(
        "DocumentChunk",
        back_populates="document",
        cascade="all, delete-orphan",
    )

    def __repr__(self) -> str:
        return f"<Document id={self.id} filename={self.filename!r}>"


class DocumentChunk(Base):
    '''A chunk of a document with its embedding, for similarity search.'''

    __tablename__ = "document_chunks"

    id = Column(Integer, primary_key=True, autoincrement=True)
    document_id = Column(
        Integer,
        ForeignKey("documents.id", ondelete="CASCADE"),
        nullable=False,
    )
    content = Column(Text, nullable=False)               # 500-1000 chars
    chunk_index = Column(Integer, nullable=False)        # position in the document: 0, 1, 2, ...
    embedding = Column(Vector(EMBEDDING_DIM), nullable=False)  # pgvector, 384 dim

    document = relationship("Document", back_populates="chunks")

    __table_args__ = (
        UniqueConstraint("document_id", "chunk_index", name="uq_doc_chunk_idx"),
        Index("ix_chunks_document_id", "document_id"),
    )

    def __repr__(self) -> str:
        return f"<DocumentChunk id={self.id} doc={self.document_id} idx={self.chunk_index}>"
