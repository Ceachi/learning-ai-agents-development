'''
Document extraction pipeline (Lesson 3): Load -> Chunk -> Extract -> Save.

Public API:
  - load_document          : LOAD step (registry over file extension)
  - should_chunk, chunk_documents : CHUNK step
  - Invoice, Contract, Product    : Pydantic schemas (EXTRACT target)
  - ExtractionPipeline     : the reusable pipeline (process)
  - EXTRACTION_REGISTRY    : routing by document type
  - extract_document       : high-level Load->Chunk->Extract->Save entry point
  - save_json              : SAVE step
'''

from .chunking import chunk_documents, should_chunk
from .loaders import LOADER_REGISTRY, load_document
from .pipeline import EXTRACTION_REGISTRY, ExtractionPipeline, extract_document
from .schemas import Contract, Invoice, Product
from .storage import save_json

__all__ = [
    "load_document",
    "LOADER_REGISTRY",
    "should_chunk",
    "chunk_documents",
    "Invoice",
    "Contract",
    "Product",
    "ExtractionPipeline",
    "EXTRACTION_REGISTRY",
    "extract_document",
    "save_json",
]
