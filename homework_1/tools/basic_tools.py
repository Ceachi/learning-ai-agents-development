'''
calculator, get_datetime, web_search

Basic tools registered via @register_tool. With docstring
'''

import ast
import operator
from datetime import datetime
from zoneinfo import ZoneInfo

from .registry import register_tool
from .params_models import (
    CalculatorParams,
    GetDatetimeParams,
    WebSearchParams,
)

# Safe operators allowed in calculator expression (avoid eval () - code injection)

_ALLOWED_OPERATORS = {
    ast.Add: operator.add,
    ast.Sub: operator.sub,
    ast.Mult: operator.mul,
    ast.Div: operator.truediv,
    ast.Mod: operator.mod,
    ast.Pow: operator.pow,
    ast.USub: operator.neg,
    ast.UAdd: operator.pos,
}

def _safe_eval(node):
    '''Recursively evaluate a Python AST node using only whitelisted operators.'''
    if isinstance(node, ast.Constant) and isinstance(node.value, (int, float)):
        return node.value
    if isinstance(node, ast.BinOp):
        op = _ALLOWED_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Operator not allowed: {type(node.op).__name__}")
        return op(_safe_eval(node.left), _safe_eval(node.right))
    if isinstance(node, ast.UnaryOp):
        op = _ALLOWED_OPERATORS.get(type(node.op))
        if op is None:
            raise ValueError(f"Unary operator not allowed: {type(node.op).__name__}")
        return op(_safe_eval(node.operand))
    raise ValueError(f"Unsupported expression element: {type(node).__name__}")

@register_tool
def calculator(params: CalculatorParams) -> str:
    '''
    Performs arithmetic on a math expression and returns the result as a string.
    Use it for any calculation beyond 2-3 digit numbers, or when precision matters.
    Supported operators: + - * / % ** and unary +/-.
    Example input: "1847 * 394" → "727718".
    '''
    try:
        tree = ast.parse(params.expression, mode="eval")
        result = _safe_eval(tree.body)
        return str(result)
    except ZeroDivisionError:
        return "Error: division by zero"
    except Exception as e:
        return f"Error: invalid expression '{params.expression}' ({e})"

@register_tool
def get_datetime(params: GetDatetimeParams) -> str:
    '''
    Returns the current date and time in ISO 8601 format for a given timezone.
    Use it whenever the user asks about the current time, today's date, or any
    time-relative computation (e.g. "days until X"). Defaults to UTC.
    Example input: timezone="Europe/Bucharest" → "2026-05-21T18:30:00+03:00".
    '''
    try:
        tz = ZoneInfo(params.timezone)
        return datetime.now(tz).isoformat(timespec="seconds")
    except Exception as e:
        return f"Error: unknown timezone '{params.timezone}' ({e})"
    

@register_tool
def web_search(params: WebSearchParams) -> str:
    '''
    Searches the web with DuckDuckGo and returns the top results as a readable list.
    Use it when the answer requires fresh or external information that is not
    in the conversation context (news, current events, prices, niche facts).
    Do NOT use it for general knowledge the LLM already knows.
    Example input: query="OpenAI GPT-5 release date", max_results=3.
    '''
    # Lazy import: keep the package optional so the rest of the agent works even
    # if `ddgs` is not installed yet. DuckDuckGo needs no API key.
    try:
        from ddgs import DDGS
    except ImportError:
        return (
            "Error: web search is unavailable — the 'ddgs' package is not installed. "
            "Install it with: pip install ddgs"
        )

    try:
        results = DDGS().text(params.query, max_results=params.max_results)
    except Exception as e:
        return f"Error: web search failed for '{params.query}' ({e})"

    if not results:
        return f"No web results found for '{params.query}'."

    lines = []
    for i, result in enumerate(results, start=1):
        title = (result.get("title") or "").strip()
        body = (result.get("body") or "").strip()
        href = (result.get("href") or "").strip()
        lines.append(f"{i}. {title}\n   {body}\n   {href}")
    return "\n".join(lines)