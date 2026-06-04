'''
LOADER_REGISTRY + load_document — the LOAD step of the pipeline (Lesson 3, §1).

A single entry point that parses any supported format (PDF / DOCX / TXT / CSV)
and always returns the same shape: a list of langchain_core Document objects
(page_content + metadata).

Registry Pattern — same idea as TOOL_REGISTRY (Phase 1): a new format is one
line in the dict, with zero changes to load_document().

Why community loaders (L3 §1): tested + maintained, uniform .load() API, they
handle edge cases (encoding, corrupt PDFs) so we don't hand-roll parsing.
'''

from pathlib import Path

from langchain_community.document_loaders import (
    CSVLoader,
    Docx2txtLoader,
    PyPDFLoader,
    TextLoader,
)
from langchain_core.documents import Document


def _text_loader(path: str) -> TextLoader:
    # TextLoader needs explicit UTF-8 so Romanian diacritics (ă, î, ș, ț) survive.
    # cp1250 vs UTF-8 is the classic TXT encoding bug called out in L3 §1.
    return TextLoader(path, encoding="utf-8")


# Registry: file extension -> loader factory.
# Each entry is a callable(path) -> loader exposing .load().
LOADER_REGISTRY: dict[str, callable] = {
    "pdf": PyPDFLoader,        # 1 Document per page (metadata includes page number)
    "docx": Docx2txtLoader,    # 1 Document for the whole file (text only)
    "txt": _text_loader,       # 1 Document; UTF-8 enforced for diacritics
    "csv": CSVLoader,          # 1 Document per row
}


def load_document(path: str) -> list[Document]:
    '''
    Load any supported document into a uniform list[Document].

    Raises:
      - ValueError          if the extension is not in LOADER_REGISTRY (.xlsx, .pptx, ...)
      - FileNotFoundError   if the path does not exist (left to propagate; the
                            pipeline/tool layer turns it into a readable message)
    '''
    p = Path(path)
    ext = p.suffix.lstrip(".").lower()
    if ext not in LOADER_REGISTRY:
        raise ValueError(
            f"Unsupported file type: .{ext} "
            f"(supported: {', '.join(sorted(LOADER_REGISTRY))})"
        )
    # Check existence up front: community loaders wrap a missing file in a generic
    # RuntimeError, but the pipeline/tool layer wants a clean FileNotFoundError.
    if not p.is_file():
        raise FileNotFoundError(f"File not found: {path}")
    return LOADER_REGISTRY[ext](path).load()
