'''
Database layer: PostgreSQL + pgvector storage with the Repository pattern.

Public API:
  - Base, engine, SessionLocal, transaction : SQLAlchemy setup + unit-of-work
  - Document, DocumentChunk                 : ORM models (one-to-many)
  - DocumentRepository, ChunkRepository      : CRUD + queries / similarity search
  - DocumentError + subclasses              : domain exceptions
'''

from .database import Base, SessionLocal, engine, transaction
from .exceptions import (
    DocumentError,
    DocumentNotFoundError,
    DuplicateDocumentError,
    InvalidMetadataError,
)
from .models import Document, DocumentChunk
from .repositories import ChunkRepository, DocumentRepository

__all__ = [
    "Base",
    "engine",
    "SessionLocal",
    "transaction",
    "Document",
    "DocumentChunk",
    "DocumentRepository",
    "ChunkRepository",
    "DocumentError",
    "DocumentNotFoundError",
    "DuplicateDocumentError",
    "InvalidMetadataError",
]
