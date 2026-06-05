'''
Chunking — the CHUNK step of the pipeline.

Chunk ONLY when a document does not fit comfortably in the context window; a
small document (< ~4000 chars) goes straight to the LLM.

Defaults: chunk_size=1000, overlap=100, using RecursiveCharacterTextSplitter
(paragraphs -> lines -> words -> chars), which keeps the semantic structure intact.
'''

from langchain_core.documents import Document
from langchain_text_splitters import RecursiveCharacterTextSplitter


def should_chunk(docs: list[Document], max_size: int = 4000) -> bool:
    '''
    Decide whether the loaded document needs chunking.

    Returns True when the combined page_content exceeds max_size characters.
    (an invoice ~2K chars -> no; a contract/report -> yes.)
    '''
    total = sum(len(doc.page_content) for doc in docs)
    return total > max_size


def chunk_documents(
    docs: list[Document],
    chunk_size: int = 1000,
    chunk_overlap: int = 100,
) -> list[Document]:
    '''
    Split documents into overlapping chunks with RecursiveCharacterTextSplitter.

    chunk_overlap (~10-20% of chunk_size) prevents "broken context" at chunk
    boundaries. Metadata from the source documents is preserved on each chunk.
    '''
    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size,
        chunk_overlap=chunk_overlap,
        # Order: paragraphs -> lines -> words -> characters (most natural first).
        separators=["\n\n", "\n", " ", ""],
    )
    return splitter.split_documents(docs)
