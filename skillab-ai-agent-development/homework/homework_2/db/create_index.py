'''
HNSW index management for document_chunks.embedding.

Linear scan is O(n) — fine under ~10K chunks, unacceptable at scale. The HNSW
index brings query time to O(log n). Index creation is a separate, idempotent
script (DROP IF EXISTS + CREATE) rather than a migration: in production you'd build
it with CREATE INDEX CONCURRENTLY after loading data, so it doesn't lock the table.

Run:  python -m db.create_index
'''

import logging

from sqlalchemy import text

from .database import engine

logger = logging.getLogger(__name__)

INDEX_NAME = "ix_chunks_embedding_hnsw"
TABLE = "document_chunks"
COLUMN = "embedding"


def create_index() -> str:
    '''(Re)build the HNSW cosine index; returns the index size as a string.'''
    with engine.begin() as conn:
        # 1. Drop if it exists (idempotent).
        conn.execute(text(f"DROP INDEX IF EXISTS {INDEX_NAME}"))
        # 2. Build HNSW with cosine ops (matches the <=> operator / cosine_distance).
        #    Recommended defaults: m=16, ef_construction=64.
        conn.execute(
            text(
                f"""
                CREATE INDEX {INDEX_NAME}
                ON {TABLE}
                USING hnsw ({COLUMN} vector_cosine_ops)
                WITH (m = 16, ef_construction = 64)
                """
            )
        )
        # 3. Verify it exists and report its size (RAM planning).
        size = conn.execute(
            text("SELECT pg_size_pretty(pg_relation_size(:idx))"),
            {"idx": INDEX_NAME},
        ).scalar()
    logger.info("Index %s created, size=%s", INDEX_NAME, size)
    return size


if __name__ == "__main__":
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    create_index()
