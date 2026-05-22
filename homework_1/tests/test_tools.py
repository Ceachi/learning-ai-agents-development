'''
Smoke tests for the tools subsystem (no LLM calls).

Covers: registration, execution, Pydantic validation, safe calculator,
error handling, and the provider catalogs.
'''

import pytest

from tools import ToolWrapper
from tools.registry import TOOL_REGISTRY


def test_builtin_tools_are_registered():
    assert {"calculator", "get_datetime", "web_search"} <= set(TOOL_REGISTRY)


def test_registry_entry_shape():
    entry = TOOL_REGISTRY["calculator"]
    assert set(entry) == {"func", "params_model", "description"}
    assert len(entry["description"]) >= 15  # docstring contract


def test_calculator_computes_correctly():
    assert ToolWrapper.call("calculator", {"expression": "1847 * 394"}) == "727718"


def test_calculator_rejects_unsafe_expression():
    # AST whitelist must block anything that is not plain arithmetic.
    result = ToolWrapper.call("calculator", {"expression": "__import__('os').system('echo hi')"})
    assert result.startswith("Error")


def test_calculator_handles_division_by_zero():
    result = ToolWrapper.call("calculator", {"expression": "1 / 0"})
    assert "zero" in result.lower()


def test_get_datetime_returns_iso_string():
    result = ToolWrapper.call("get_datetime", {"timezone": "UTC"})
    # ISO 8601 starts with YYYY-MM-DD and is not an error string.
    assert not result.startswith("Error")
    assert result[4] == "-" and result[7] == "-"


def test_invalid_arguments_are_caught_by_pydantic():
    result = ToolWrapper.call("calculator", {"wrong_param": "2+2"})
    assert "invalid arguments" in result.lower()


def test_unknown_tool_returns_error():
    assert "not found" in ToolWrapper.call("does_not_exist", {}).lower()


def test_catalog_anthropic_shape():
    catalog = ToolWrapper.catalog("anthropic")
    assert len(catalog) == len(TOOL_REGISTRY)
    for tool in catalog:
        assert set(tool) == {"name", "description", "input_schema"}


def test_catalog_openai_shape():
    catalog = ToolWrapper.catalog("openai")
    assert all(tool["type"] == "function" for tool in catalog)


def test_catalog_unknown_provider_raises():
    with pytest.raises(ValueError):
        ToolWrapper.catalog("grok")
