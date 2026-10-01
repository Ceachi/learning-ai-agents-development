'''
RAG layer: embeddings, similarity search, and document indexing.

Public API:
  - RAGService       : embed / search / get_context over DocumentChunks
  - MODEL_NAME       : the sentence-transformers model (multilingual, 384-dim)
  - DEFAULT_THRESHOLD: minimum cosine similarity kept for RAG context
  - index_document   : Load -> Extract -> save Document + embedded chunks
'''

from .indexing import index_document, index_documents
from .service import DEFAULT_THRESHOLD, MODEL_NAME, RAGService

__all__ = [
    "RAGService",
    "MODEL_NAME",
    "DEFAULT_THRESHOLD",
    "index_document",
    "index_documents",
]
