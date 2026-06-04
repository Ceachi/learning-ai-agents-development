'''
Smoke tests for the extraction pipeline (no LLM calls).

Covers the LOAD / CHUNK / SCHEMA / SAVE steps and the agent-tool registration.
The actual EXTRACT step needs a live LLM + API key, so it is exercised separately
(see the demo in the homework writeup), not here.
'''

import json
from pathlib import Path

import pytest

from extraction import (
    EXTRACTION_REGISTRY,
    LOADER_REGISTRY,
    Contract,
    Invoice,
    Product,
    chunk_documents,
    load_document,
    save_json,
    should_chunk,
)
from extraction.pipeline import ExtractionPipeline
from tools import ToolWrapper
from tools.registry import TOOL_REGISTRY

SAMPLES = Path("samples")


# --------------------------------------------------------------------------- #
# LOAD                                                                         #
# --------------------------------------------------------------------------- #
def test_loader_registry_has_four_formats():
    assert set(LOADER_REGISTRY) == {"pdf", "docx", "txt", "csv"}


def test_load_txt_returns_documents():
    docs = load_document(str(SAMPLES / "factura_001.txt"))
    assert docs and docs[0].page_content.strip()


def test_load_txt_keeps_romanian_diacritics():
    # UTF-8 must be enforced so "TOTAL DE PLATĂ" / "Semnătura" stay intact.
    text = "\n".join(d.page_content for d in load_document(str(SAMPLES / "factura_001.txt")))
    assert "PLATĂ" in text


def test_load_csv_returns_one_document_per_row():
    docs = load_document(str(SAMPLES / "facturi_export.csv"))
    assert len(docs) == 10  # 10 data rows in facturi_export.csv


def test_unsupported_extension_raises_value_error():
    with pytest.raises(ValueError):
        load_document("ceva.xlsx")


# --------------------------------------------------------------------------- #
# CHUNK                                                                        #
# --------------------------------------------------------------------------- #
def test_should_chunk_false_for_small_invoice():
    docs = load_document(str(SAMPLES / "factura_001.txt"))
    assert should_chunk(docs) is False  # ~1.4K chars < 4K threshold


def test_should_chunk_true_for_large_text():
    from langchain_core.documents import Document

    big = [Document(page_content="x" * 5000)]
    assert should_chunk(big) is True


def test_chunk_documents_splits_and_keeps_metadata():
    from langchain_core.documents import Document

    docs = [Document(page_content="abc def ghi " * 500, metadata={"source": "x"})]
    chunks = chunk_documents(docs, chunk_size=200, chunk_overlap=20)
    assert len(chunks) > 1
    assert chunks[0].metadata["source"] == "x"


# --------------------------------------------------------------------------- #
# SCHEMAS                                                                      #
# --------------------------------------------------------------------------- #
def test_invoice_schema_roundtrip():
    inv = Invoice(
        numar="FV-2024-001",
        data="2024-03-15",
        total=18088.0,
        produse=[Product(denumire="Laptop", cantitate=2, pret_unitar=4500, total=9000)],
    )
    dumped = inv.model_dump()
    assert dumped["numar"] == "FV-2024-001"
    assert dumped["produse"][0]["denumire"] == "Laptop"


def test_contract_schema_defaults_lists():
    c = Contract(numar="CS-2024-015", data_incheiere="2024-03-01")
    assert c.obligatii_prestator == []  # optional list defaults to empty


# --------------------------------------------------------------------------- #
# SAVE                                                                         #
# --------------------------------------------------------------------------- #
def test_save_json_writes_file(tmp_path):
    inv = Invoice(numar="FV-2024-001", data="2024-03-15", total=18088.0)
    path = save_json(inv, "factura", output_dir=str(tmp_path))
    assert path.exists()
    data = json.loads(path.read_text(encoding="utf-8"))
    assert data["numar"] == "FV-2024-001"


def test_save_json_sanitizes_slash_in_number(tmp_path):
    inv = Invoice(numar="2024/001", data="2024-03-15", total=1.0)
    path = save_json(inv, "factura", output_dir=str(tmp_path))
    assert path.name == "2024_001.json"


# --------------------------------------------------------------------------- #
# PIPELINE wiring (no LLM call)                                                #
# --------------------------------------------------------------------------- #
def test_extraction_registry_routes_types():
    assert EXTRACTION_REGISTRY["factura"]["schema"] is Invoice
    assert EXTRACTION_REGISTRY["contract"]["schema"] is Contract
    assert EXTRACTION_REGISTRY["factura"]["chunk_size"] is None  # invoices not chunked


def test_pipeline_instantiates_without_api_key():
    # The LLM client is lazy, so building the pipeline must not require a key.
    p = ExtractionPipeline()
    assert p._llm is None


# --------------------------------------------------------------------------- #
# AGENT TOOLS                                                                  #
# --------------------------------------------------------------------------- #
def test_extraction_tools_registered():
    assert {"extract_invoice_tool", "extract_contract_tool"} <= set(TOOL_REGISTRY)


def test_extraction_tools_have_descriptive_docstrings():
    for name in ("extract_invoice_tool", "extract_contract_tool"):
        assert len(TOOL_REGISTRY[name]["description"]) >= 15


def test_extraction_tools_in_catalog():
    names = {t["name"] for t in ToolWrapper.catalog("anthropic")}
    assert {"extract_invoice_tool", "extract_contract_tool"} <= names


def test_invoice_tool_missing_file_returns_error_dict():
    # No LLM call: load_document fails first with FileNotFoundError, handled to a dict.
    result = ToolWrapper.call("extract_invoice_tool", {"file_path": "samples/nope.txt"})
    assert "'success': false" in result.lower()
    assert "not found" in result.lower()  # "File not found: ..."
