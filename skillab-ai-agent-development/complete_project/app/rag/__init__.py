"""
RAG Module - Embedding and semantic search.

Usage:
    from app.db import transaction
    from app.rag import RAGService

    with transaction() as session:
        rag = RAGService(session)
        results = rag.search("query", top_k=5)
"""
from .service import RAGService, get_embedding_model

__all__ = ["RAGService", "get_embedding_model"]
