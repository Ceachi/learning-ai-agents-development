'''
save_json — the SAVE step of the pipeline.

Writes an extracted Pydantic object to extracted_data/<doc_type>/<numar>.json,
organized per document type (facturi/, contracte/). mkdir(parents=True,
exist_ok=True) creates missing folders without error. ensure_ascii=False keeps
Romanian diacritics readable in the JSON file.
'''

import json
import re
from pathlib import Path

from pydantic import BaseModel


def _safe_filename(value: str) -> str:
    '''Make a document number safe to use as a filename (no slashes/spaces).'''
    cleaned = value.strip().replace("/", "_").replace("\\", "_")
    cleaned = re.sub(r"\s+", "_", cleaned)
    return cleaned or "document"


def save_json(data: BaseModel, doc_type: str, output_dir: str = "extracted_data") -> Path:
    '''
    Persist an extracted object as JSON under output_dir/doc_type/.

    The filename is derived from the object's `numar` field (Invoice and Contract
    both have it). Returns the path written.
    '''
    out = Path(output_dir) / doc_type
    out.mkdir(parents=True, exist_ok=True)

    numar = getattr(data, "numar", None) or "document"
    path = out / f"{_safe_filename(str(numar))}.json"

    with open(path, "w", encoding="utf-8") as f:
        json.dump(data.model_dump(), f, indent=2, ensure_ascii=False)

    return path
