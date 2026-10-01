'''
search_documents — RAG retrieval exposed as an agent tool.

Wraps RAGService as a tool on the ReAct agent so it answers questions grounded in
the indexed documents. Registered with @register_tool; returns a citable context
STRING (filename + chunk + relevance) which the agent reads as an observation and
cites the source — and never a raw exception.
'''

from pydantic import BaseModel, Field

from db import transaction
from rag import RAGService

from .registry import register_tool


class SearchDocumentsParams(BaseModel):
    '''Parameters for searching the indexed documents.'''

    query: str = Field(
        description="Natural-language question/search over the loaded documents "
        "(invoices, contracts): clauses, amounts, deadlines, obligations, termination.",
        min_length=2,
    )


@register_tool
def search_documents(params: SearchDocumentsParams) -> str:
    '''
    Search the loaded documents (invoices, contracts) and return the most relevant
    excerpts with their source. Use this whenever the user asks about the CONTENT of
    documents — clauses, amounts, deadlines, obligations, termination ("reziliere"),
    penalties — so the answer is grounded in real documents and the source can be cited.
    '''
    try:
        with transaction() as db:
            results = RAGService(db).search(params.query, top_k=3)
            if not results:
                return "Nu am găsit informații relevante în documente."
            # Build the citable context while the session is open.
            return "\n\n".join(
                f"[{chunk.document.filename} | chunk {chunk.chunk_index} | "
                f"relevanță {score:.0%}]\n{chunk.content}"
                for chunk, score in results
            )
    except Exception as e:
        # Never surface a raw traceback — the agent reads this as an observation.
        return f"Eroare la căutarea în documente: {e}"
