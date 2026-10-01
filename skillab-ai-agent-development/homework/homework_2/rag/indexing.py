'''
index_document — the RAG "offline index" step.

Load → (optional) extract metadata → save a Document → chunk → embed → save
DocumentChunks, all in one transaction. The save is idempotent on filename.

Reuses load_document / chunk_documents / extract_document from the extraction
pipeline — no duplication.
'''

import logging
from pathlib import Path

from tqdm import tqdm

from db import ChunkRepository, Document, DocumentRepository, transaction
from extraction import chunk_documents, extract_document, load_document

from .service import RAGService

logger = logging.getLogger(__name__)


def index_document(
    file_path: str,
    doc_type: str | None = None,
    # Default chunking: size 800, overlap 100.
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> Document:
    '''
    Ingest a file into the database for RAG: Document + its embedded chunks.

    If `doc_type` is given ("factura"/"contract"), the structured extraction is
    stored in doc_metadata so it stays queryable.

    Idempotent on filename: re-indexing the same file returns the existing Document
    without duplicating it.
    '''
    path = Path(file_path)

    # 1. Load (loader registry) + full text.
    docs = load_document(str(path))
    content = "\n\n".join(d.page_content for d in docs)

    # 2. Optionally extract structured metadata (Invoice/Contract) → doc_metadata.
    metadata: dict = {}
    if doc_type:
        extracted = extract_document(str(path), doc_type, save=False)
        metadata = {"doc_type": doc_type, **extracted.model_dump()}

    with transaction() as db:
        repo = DocumentRepository(db)

        # 3. Idempotent save: skip if this filename is already indexed.
        existing = repo.get_by_filename(path.name)
        if existing is not None:
            logger.info("Skip duplicate: %s (id=%d)", path.name, existing.id)
            return existing

        document = repo.create(filename=path.name, content=content, metadata=metadata)

        # 4. Chunk → embed → store (the RAG offline index).
        chunks = chunk_documents(docs, chunk_size=chunk_size, chunk_overlap=chunk_overlap)
        rag = RAGService(db)
        embeddings = rag.embed_batch([c.page_content for c in chunks])
        ChunkRepository(db).create_chunks_batch(
            [
                {
                    "document_id": document.id,
                    "content": c.page_content,
                    "chunk_index": i,
                    "embedding": emb,
                }
                for i, (c, emb) in enumerate(zip(chunks, embeddings))
            ]
        )
        logger.info(
            "Indexed %s (id=%d, chunks=%d)", path.name, document.id, len(chunks)
        )
        return document


def index_documents(
    file_paths: list[str],
    doc_type: str | None = None,
    chunk_size: int = 800,
    chunk_overlap: int = 100,
) -> list[Document]:
    '''
    Index several files, showing a tqdm progress bar over the files.

    Each file is indexed with index_document() (idempotent on filename), so
    re-running skips already-indexed files.
    '''
    return [
        index_document(path, doc_type, chunk_size, chunk_overlap)
        for path in tqdm(file_paths, desc="Indexing documents", unit="doc")
    ]
