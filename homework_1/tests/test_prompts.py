'''
Smoke tests for the prompts subsystem (no LLM calls).

Covers: YAML loading, Jinja2 rendering, variable-contract validation,
and lookup errors.
'''

import pytest

from prompts.registry import get_prompt_registry


def test_all_prompts_load():
    names = set(get_prompt_registry().list_templates())
    assert {"planner", "analyst", "summary", "extract", "reminder"} <= names


def test_planner_renders_and_resolves_all_variables():
    out = get_prompt_registry().render("planner")
    assert "IDENTITY" in out
    assert "{{" not in out and "}}" not in out  # no unresolved Jinja2


def test_render_applies_overrides():
    out = get_prompt_registry().render("summary", tone="casual")
    assert "casual" in out


def test_unknown_variable_is_rejected():
    # Typo: max_word instead of max_words must be caught before rendering.
    with pytest.raises(ValueError):
        get_prompt_registry().render("planner", max_word=100)


def test_reminder_declares_no_variables():
    # reminder.yaml has `variables: []` -> passing any variable is rejected.
    with pytest.raises(ValueError):
        get_prompt_registry().render("reminder", foo="bar")


def test_missing_prompt_raises_keyerror():
    with pytest.raises(KeyError):
        get_prompt_registry().get("does_not_exist")


def test_template_metadata_is_loaded():
    planner = get_prompt_registry().get("planner")
    assert planner.metadata is not None
    assert planner.metadata.get("category") == "agent"
    assert planner.variables == ("role", "domain", "tone", "language", "max_words")
