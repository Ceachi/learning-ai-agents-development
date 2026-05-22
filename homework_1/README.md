# QA Agent — Tools + Prompts + ReAct

A question-answering agent that orchestrates an LLM with custom tools and
externalized YAML prompts, driven by a ReAct loop (Think → Act → Observe → Repeat).

## Features

- **Tools with Pydantic** — each tool declares its parameters as a Pydantic
  `BaseModel`; a `@register_tool` decorator validates and auto-registers them.
- **Prompts as configuration** — prompts live in versioned YAML files and are
  rendered with Jinja2, with an automatic variable contract.
- **ReAct agent** — the LLM requests tools, the app executes them, results flow
  back as observations until a final answer is produced.
- **Provider-agnostic** — an `LLMFactory` supports Anthropic, OpenAI, Google,
  and Ollama (default: Anthropic).

## Project structure

```
homework_1/
├── agent.py              # LLMFactory, ReAct loop, entry points (ask/chat)
├── tools/
│   ├── params_models.py  # Pydantic BaseModel per tool
│   ├── registry.py       # TOOL_REGISTRY + @register_tool decorator
│   ├── basic_tools.py    # calculator, get_datetime, web_search
│   ├── tool_wrapper.py   # ToolWrapper.call() + catalog()
│   └── __init__.py       # exports ToolWrapper, auto-registers tools
├── prompts/
│   ├── registry.py       # PromptTemplate, PromptRegistry, hot reload
│   ├── planner.yaml      # ReAct system prompt (the agent)
│   ├── analyst.yaml      # task prompt: structured analysis
│   ├── summary.yaml      # task prompt: summarization
│   ├── extract.yaml      # task prompt: JSON field extraction
│   └── reminder.yaml     # user-message reminder wrapper
├── tests/                # smoke tests (no LLM calls)
├── conftest.py           # pytest setup
└── requirements.txt
```

API keys live in `.env` in this folder (see `.env_example`).

## Setup

```bash
# from homework_1/
pip install -r requirements.txt

# configure your key: copy the template and add your key
cp .env_example .env
# then edit .env and set ANTHROPIC_API_KEY=...
```

## Usage

### Interactive chat (console)

Run from `homework_1/`:

```bash
python agent.py
```

This starts a multi-turn conversation. History is kept across turns, and tool
calls are shown inline so you can watch the Think → Act → Observe steps.

Commands:

- `exit` / `quit` — leave
- `reset` — clear the conversation history

Example session:

```
QA Agent — chat with tools. Commands: 'exit'/'quit', 'reset'.

You> What is 25 * 17?
  [tool] calculator({'expression': '25 * 17'})
  [result] 425
Agent> 25 × 17 = 425.

You> and how many days until December 31?
  [tool] get_datetime({'timezone': 'UTC'})
  [result] 2026-05-22T10:00:00+00:00
  [tool] calculator({'expression': '...'})
  [result] 223
Agent> 223 days until December 31, 2026.

You> exit
Bye.
```

### Programmatic

```python
from agent import ask

print(ask("What is 1847 * 394?"))
print(ask("How many days until December 31?"))
```

## How it works

1. `ToolWrapper.catalog()` turns every registered tool into a JSON Schema and
   binds it to the LLM.
2. The system prompt (`planner.yaml`) instructs the model to follow the
   Think → Act → Observe loop and use only the available tools.
3. `react_loop()` invokes the LLM; if it requests tools, `execute_tool()` runs
   them via `ToolWrapper.call()` (Pydantic-validated) and feeds the results back
   as `ToolMessage`s, repeating until the model returns a final answer.
4. `max_iterations` caps the loop as a safety net against runaway cost.

### Adding a tool

```python
# tools/params_models.py
class MyToolParams(BaseModel):
    value: str = Field(description="...")

# tools/basic_tools.py
@register_tool
def my_tool(params: MyToolParams) -> str:
    '''Clear description: what it does, when to use it, an example.'''
    ...
```

The decorator enforces a single `BaseModel` parameter and a meaningful docstring
(which becomes the description the LLM sees).

### Editing a prompt

Edit the relevant `prompts/*.yaml` file. A watchdog observer reloads changes
automatically during development. System prompts hold only configuration
variables; the user's actual data is sent as the user message.

## Testing

```bash
pytest -v
```

Smoke tests cover tool registration, the safe (AST-based) calculator, Pydantic
validation, prompt loading, Jinja2 rendering, and the variable contract — all
without making LLM calls.

## Design patterns

- **Registry** — `TOOL_REGISTRY`, `PromptRegistry`
- **Decorator** — `@register_tool`
- **Factory** — `LLMFactory`
- **Singleton** — `get_prompt_registry()` (via `lru_cache`)
