"""
guardrails/schemas.py — Pydantic v2 input models for the MCP tools.

Satisfies the first half of Cerința 3:
  "Implementează input validation pe ce intră în server
   (tip, dimensiune, câmpuri permise)"

  • TYPE       → field type annotations (str, list[str], int…).
  • DIMENSIUNE → Field(min_length=…, max_length=…).
  • CÂMPURI    → model_config = ConfigDict(extra="forbid").

Pydantic raises ValidationError on any of these, which FastMCP
surfaces back to the client as a JSON-RPC error — no manual checks.
"""

from pydantic import BaseModel, ConfigDict, Field


MAX_QUERY_CHARS = 2000   # tunable upper bound for any natural-language query


class DataAnalystInput(BaseModel):
    """Input schema for the `data_analyst` MCP tool (Cerința 1)."""

    # Reject unknown fields — only `query` and `tables` are allowed.
    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=1,
        max_length=MAX_QUERY_CHARS,
        description="Natural-language question for the Data Analyst agent.",
    )
    tables: list[str] | None = Field(
        default=None,
        description="Optional list of table names to restrict the analysis to.",
    )


class OrchestratorInput(BaseModel):
    """Input schema for the `orchestrator` MCP tool (Cerința 2)."""

    model_config = ConfigDict(extra="forbid")

    query: str = Field(
        min_length=1,
        max_length=MAX_QUERY_CHARS,
        description="Natural-language question for the RAG Orchestrator agent.",
    )
