"""
mcp_server.py — HW5 MCP server.

Single FastMCP server that exposes two agents from `homework_3/` as
MCP tools, fronted by the guardrails from `guardrails/`:

    Cerința 1 → tool `data_analyst`  (homework_3.analyst_agent / NL2SQL)
    Cerința 2 → tool `orchestrator`  (homework_3.orchestrator / RAG supervisor)
    Cerința 3 → Pydantic schemas + InputValidator (regex + LLM-Judge)
                run on every tool call before the agent is invoked.

Transport: HTTP on 127.0.0.1:8000/mcp — production-shaped, easy to
wire into Claude Code.

Run:
    python mcp_server.py
"""

from __future__ import annotations

import sys
from pathlib import Path


# ─── Boot block ────────────────────────────────────────────────────────
# Make the homework_3 agents importable WITHOUT copying any of their code
# here. Both paths must be on sys.path before we touch anything in HW3:
#   • homework_3/skillab-py/src — for `from skillab import get_llm`
#   • homework_3/src            — for `from orchestrator import …` etc.
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT / "homework_3" / "src"))
sys.path.insert(0, str(ROOT / "homework_3" / "skillab-py" / "src"))

from dotenv import load_dotenv
load_dotenv()

from fastmcp import FastMCP

# Agents (imported directly from homework_3/src/)
from skillab import get_llm
from orchestrator import Orchestrator
from analyst_agent import AnalystAgent
from state import OrchestratorState

# HW5 guardrails
from guardrails.schemas import DataAnalystInput, OrchestratorInput
from guardrails.input_validator import InputValidator


# ─── MCP server + shared guardrail validator ───────────────────────────
mcp = FastMCP("hw5-agents")
validator = InputValidator(use_llm=True)


# ─── Lazy-initialized agents (created on first tool call) ──────────────
# We don't build the LangGraph compiled apps at import time because they
# need DB access (RAG agent connects to pgvector) which would block the
# server from starting if Postgres isn't up yet.
_orchestrator_app = None
_analyst = None


def _get_orchestrator():
    global _orchestrator_app
    if _orchestrator_app is None:
        llm = get_llm()
        _orchestrator_app = Orchestrator(llm=llm).build_graph()
    return _orchestrator_app


def _get_analyst():
    global _analyst
    if _analyst is None:
        llm = get_llm()
        data_dir = ROOT / "homework_3" / "data" / "nl2sql_agent"
        _analyst = AnalystAgent(
            tables_config={
                "achizitii_directe": {
                    "schema_path": str(data_dir / "schema_achizitii_directe.json"),
                    "business_path": str(data_dir / "business_achizitii_directe.json"),
                },
                "anunturi_initiere": {
                    "schema_path": str(data_dir / "schema_anunturi_initiere.json"),
                    "business_path": str(data_dir / "business_anunturi_initiere.json"),
                },
            },
            llm=llm,
        )
    return _analyst


# ─── Cerința 1 · Data Analyst ──────────────────────────────────────────
@mcp.tool()
def data_analyst(query: str, tables: list[str] | None = None) -> dict:
    """Run the Data Analyst (NL2SQL) agent on a natural-language question.

    Inspects multi-table SQL datasets (achizitii_directe, anunturi_initiere)
    and returns a structured answer with the SQL it executed.

    Args:
        query: The natural-language question. Max 2000 chars.
        tables: Optional list of table names to restrict the analysis to.
    """
    # Cerința 3a — input validation (type + size + allowed fields)
    parsed = DataAnalystInput(query=query, tables=tables)

    # Cerința 3b — prompt-injection guardrail (regex + LLM-Judge)
    r = validator.validate(parsed.query)
    if not r.passed:
        raise ValueError(f"Blocked by {r.method}: {r.details}")

    # Cerința 1 — handler that calls the agent
    analyst = _get_analyst()
    result = analyst.chat(parsed.query)
    return {"status": result.get("status"), "answer": result.get("answer")}


# ─── Cerința 2 · Orchestrator ──────────────────────────────────────────
@mcp.tool()
def orchestrator(query: str) -> dict:
    """Run the Orchestrator (RAG supervisor) agent on a natural-language question.

    Coordinates a RAG worker over the pgvector document store; loops
    evaluate → refine up to 3 times until it can answer.

    Args:
        query: The natural-language question. Max 2000 chars.
    """
    # Cerința 3a — input validation
    parsed = OrchestratorInput(query=query)

    # Cerința 3b — prompt-injection guardrail
    r = validator.validate(parsed.query)
    if not r.passed:
        raise ValueError(f"Blocked by {r.method}: {r.details}")

    # Cerința 2 — handler that calls the agent
    app = _get_orchestrator()
    result = app.invoke(OrchestratorState(query=parsed.query))
    return {"status": result.get("status"), "answer": result.get("answer")}


# ─── Run ───────────────────────────────────────────────────────────────
if __name__ == "__main__":
    print("🚀 hw5-agents on http://127.0.0.1:8000/mcp")
    print("📋 Tools: data_analyst, orchestrator (both guardrailed)")
    print("🛡  Guardrails: Pydantic schemas + InputValidator (regex + LLM-Judge)")
    mcp.run(transport="http", host="127.0.0.1", port=8000)
