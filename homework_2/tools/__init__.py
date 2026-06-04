'''
Export ToolWrapper and auto-register all built-in tools.
'''

from .tool_wrapper import ToolWrapper
from . import basic_tools  # noqa: F401 — imported for its @register_tool side effects
from . import extraction_tools  # noqa: F401 — registers extract_invoice_tool / extract_contract_tool

__all__ = ["ToolWrapper"]