'''
RAGService — embeddings + similarity search.

  - MODEL_NAME is a multilingual model suited to Romanian documents
    (paraphrase-multilingual-MiniLM-L12-v2, 384-dim).
  - sentence_transformers is imported lazily inside the `model` property, keeping
    the heavy dependency out of the import path for the rest of the app and the
    test suite.
'''

from sqlalchemy.orm import Session

from db.models import DocumentChunk
from db.repositories import ChunkRepository

MODEL_NAME = "paraphrase-multilingual-MiniLM-L12-v2"
DEFAULT_THRESHOLD = 0.4


class RAGService:
    '''Generates embeddings and runs cosine similarity search over chunks.'''

    _model = None  # singleton per process — the model (~80MB) loads once

    def __init__(self, db: Session) -> None:
        self.repo = ChunkRepository(db)

    @property
    def model(self):
        '''Lazy + shared SentenceTransformer (loaded once per process).'''
        if RAGService._model is None:
            from sentence_transformers import SentenceTransformer

            RAGService._model = SentenceTransformer(MODEL_NAME)
        return RAGService._model

    def embed(self, text: str) -> list[float]:
        '''Embed a single text into a 384-dim vector.'''
        return self.model.encode(text, convert_to_numpy=True).tolist()

    def embed_batch(self, texts: list[str]) -> list[list[float]]:
        '''Embed many texts in one batched call (used when indexing chunks).'''
        embeddings = self.model.encode(
            texts, convert_to_numpy=True, show_progress_bar=len(texts) > 1
        )
        return [e.tolist() for e in embeddings]

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[tuple[DocumentChunk, float]]:
        '''Embed the query and return the top-k nearest chunks with scores.'''
        query_emb = self.embed(query)
        return self.repo.similarity_search(query_emb, top_k=top_k)

    def get_context(
        self,
        query: str,
        top_k: int = 5,
        threshold: float = DEFAULT_THRESHOLD,
    ) -> str:
        '''
        Build a citable context string from the relevant chunks.

        Returns "" when nothing scores at or above `threshold` — the caller turns
        that into a clear "no relevant info" answer instead of hallucinating.
        '''
        results = self.search(query, top_k=top_k)
        relevant = [(chunk, score) for chunk, score in results if score >= threshold]
        if not relevant:
            return ""
        return "\n\n".join(
            f"[{chunk.document.filename}] {chunk.content}" for chunk, _ in relevant
        )
