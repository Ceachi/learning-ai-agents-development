"""MCP Server - Exposes agents as tools for Claude Code / MCP clients."""
import logging

from fastmcp import FastMCP

from app.agents import AnalystAgent, Orchestrator, route
from app.guardrails import guard
from app.llm import get_llm

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

mcp = FastMCP(
    name="document-analyst",
    description="Document analysis and SEAP data queries",
)

# Lazy singletons
_orchestrator: Orchestrator | None = None
_analyst: AnalystAgent | None = None

_TABLES_CONFIG = {
    "achizitii_directe": {"schema_path": "data/schemas/achizitii_directe.json"},
    "anunturi_initiere": {"schema_path": "data/schemas/anunturi_initiere.json"},
}


def _get_orchestrator() -> Orchestrator:
    global _orchestrator
    if _orchestrator is None:
        _orchestrator = Orchestrator(llm=get_llm())
    return _orchestrator


def _get_analyst() -> AnalystAgent:
    global _analyst
    if _analyst is None:
        _analyst = AnalystAgent(tables_config=_TABLES_CONFIG, llm=get_llm())
    return _analyst


def _guard_check(query: str) -> dict | None:
    """Run guardrails, return error dict if blocked."""
    result = guard(query, use_llm_injection=False)
    if not result.safe:
        return {"answer": result.message, "status": "blocked"}
    return None


@mcp.tool()
def search_documents(query: str) -> dict:
    """Search documents using RAG (semantic search over SEAP documentation)."""
    if blocked := _guard_check(query):
        return blocked

    logger.info(f"[MCP] search_documents: {query[:50]}...")
    result = _get_orchestrator().run(query)

    return {
        "answer": result.answer or "Nu am găsit informații.",
        "status": result.status,
        "iterations": result.iteration,
    }


@mcp.tool()
def analyze_data(query: str) -> dict:
    """Query SEAP database using natural language (converts to SQL)."""
    if blocked := _guard_check(query):
        return blocked

    logger.info(f"[MCP] analyze_data: {query[:50]}...")
    result = _get_analyst().run(query)

    return {
        "answer": result.answer or "Nu am putut analiza datele.",
        "status": result.status,
    }


@mcp.tool()
def ask(query: str) -> dict:
    """Auto-route query to RAG or SQL based on intent classification."""
    if blocked := _guard_check(query):
        return {**blocked, "method": "none"}

    logger.info(f"[MCP] ask: {query[:50]}...")
    intent = route(query)

    if intent == "rag":
        result = _get_orchestrator().run(query)
    else:
        result = _get_analyst().run(query)

    return {
        "answer": result.answer or "Nu am putut genera un răspuns.",
        "status": result.status,
        "method": intent,
    }


if __name__ == "__main__":
    import uvicorn
    from fastmcp.server.sse import create_sse_app

    app = create_sse_app(mcp)
    uvicorn.run(app, host="0.0.0.0", port=8000)
