'''
extract_invoice_tool + extract_contract_tool — the ExtractionPipeline exposed as
agent tools (Lesson 3, §5: Chat Agent integration).

Each tool wraps the pure business logic (extraction.extract_document) behind a
Pydantic params model + a descriptive docstring. The agent reads the docstrings
and picks the right tool automatically — no manual if/else.

Error handling (L3 §5, slide60): a tool ALWAYS returns a dict — never a raw
exception. The agent can read {"success": False, "error": ...} and explain it to
the user in natural language, and the ReAct loop keeps running even if a tool fails.

Note on language: docstrings, comments, and these tool-return messages are in
English (like the basic tools). The extraction schemas (extraction/schemas.py)
keep Romanian Field descriptions because they guide extraction FROM the Romanian
documents. The agent's reply language follows the user (planner.yaml `language`).
'''

from pydantic import BaseModel, Field, ValidationError

from extraction import extract_document

from .registry import register_tool


class ExtractInvoiceParams(BaseModel):
    '''Parameters for invoice extraction.'''

    file_path: str = Field(
        description="Path to the invoice file (e.g. samples/factura_001.txt). PDF, DOCX, or TXT.",
        min_length=1,
    )


class ExtractContractParams(BaseModel):
    '''Parameters for contract extraction.'''

    file_path: str = Field(
        description="Path to the contract file (e.g. samples/contract_servicii.txt). PDF, DOCX, or TXT.",
        min_length=1,
    )


def _run_extraction(file_path: str, doc_type: str) -> dict:
    '''
    Shared body for both tools: run the pipeline and ALWAYS return a dict.

    Returns {"success": True, "data": ..., "message": ...} on success,
    or {"success": False, "error": ...} on any failure (never raises).
    '''
    try:
        result = extract_document(file_path, doc_type)
        return {
            "success": True,
            "data": result.model_dump(),
            "message": f"Extracted {result.numar}, saved to extracted_data/{doc_type}/.",
        }
    except FileNotFoundError:
        return {"success": False, "error": f"File not found: {file_path}"}
    except ValueError as e:
        # Unsupported file extension from load_document.
        return {"success": False, "error": f"Unsupported file type: {e}"}
    except ValidationError as e:
        return {"success": False, "error": f"Validation failed: {e}"}
    except Exception as e:
        # Never surface a raw traceback — the agent cannot read it.
        return {"success": False, "error": f"Processing error: {e}"}


@register_tool
def extract_invoice_tool(params: ExtractInvoiceParams) -> dict:
    '''
    Extract structured data from INVOICES: numar, data, furnizor, client, produse, subtotal, tva, total.
    Use this tool when the user asks to extract or process data from an invoice or
    financial document (PDF, DOCX, TXT). Saves the result as JSON.
    '''
    return _run_extraction(params.file_path, "factura")


@register_tool
def extract_contract_tool(params: ExtractContractParams) -> dict:
    '''
    Extract structured data from CONTRACTS: numar, prestator, beneficiar, valoare, durata_luni, obligatii.
    Use this tool when the user asks to extract or process data from a service contract,
    commercial agreement, or convention (PDF, DOCX, TXT). Saves the result as JSON.
    '''
    return _run_extraction(params.file_path, "contract")
