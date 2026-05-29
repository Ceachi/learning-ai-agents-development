'''
QA Agent — orchestrates an LLM with the registered tools and YAML prompts.

Architecture:
  - LLMFactory       — Factory pattern that hides provider differences
  - LangChain client — same API across Anthropic / OpenAI / Google
  - ToolWrapper      — our custom Tool Registry
  - PromptRegistry   — YAML + Jinja2 prompts

Two entry points:
  - chat()       — one-shot: a single round of tool use.
  - react_loop() — full ReAct loop: Think → Act → Observe → Repeat.
  - ask()        — convenience wrapper that builds everything and runs react_loop().
'''

import os

from dotenv import load_dotenv
from langchain_core.messages import (
    AIMessage,
    HumanMessage,
    SystemMessage,
    ToolMessage,
)

from tools import ToolWrapper
from prompts.registry import get_prompt_registry


# Load API keys from .env into os.environ before any client is created.
load_dotenv()


# ---------------------------------------------------------------------------
# LLM Factory
# ---------------------------------------------------------------------------
class LLMFactory:
    '''
    Centralizes LLM instantiation across providers. Calling code does NOT
    need to know which SDK class to import — it just asks the factory.

    Provider SDKs are imported lazily inside each branch, so you only need
    the package for the provider you actually use (e.g. Anthropic-only setups
    don't require langchain-openai or langchain-google-genai).

    Switching provider becomes a one-line change:
        llm = LLMFactory.create("anthropic")
        llm = LLMFactory.create("openai")
        llm = LLMFactory.create("google")
    '''

    @staticmethod
    def create(provider: str, model: str | None = None, **kwargs):
        if provider == "anthropic":
            from langchain_anthropic import ChatAnthropic
            return ChatAnthropic(model=model or "claude-sonnet-4-6", **kwargs)
        if provider == "openai":
            from langchain_openai import ChatOpenAI
            return ChatOpenAI(model=model or "gpt-4o-mini", **kwargs)
        if provider == "google":
            from langchain_google_genai import ChatGoogleGenerativeAI
            return ChatGoogleGenerativeAI(model=model or "gemini-2.5-flash", **kwargs)
        if provider == "ollama":
            from langchain_ollama import ChatOllama
            return ChatOllama(
                model=model or "llama3.2",
                base_url=os.getenv("OLLAMA_BASE_URL", "http://localhost:11434"),
                **kwargs,
            )
        raise ValueError(f"Unknown provider: '{provider}'")


# ---------------------------------------------------------------------------
# Default configuration (overridable via .env)
# ---------------------------------------------------------------------------
DEFAULT_PROVIDER = os.getenv("DEFAULT_PROVIDER", "anthropic")
DEFAULT_MODEL = os.getenv("DEFAULT_MODEL", "claude-sonnet-4-6")


def build_llm():
    '''Build a tool-bound LangChain LLM ready to be invoked.'''
    llm = LLMFactory.create(DEFAULT_PROVIDER, model=DEFAULT_MODEL, temperature=0.2)
    # bind_tools accepts the OpenAI-style schema; LangChain converts it
    # to whatever the underlying provider expects.
    return llm.bind_tools(ToolWrapper.catalog("openai"))


def build_system_prompt(prompt_name: str = "planner", **overrides) -> str:
    '''
    Render a system prompt from the YAML registry.

    All defaults live in the YAML template via Jinja2's `| default(...)` filter
    (prompts are configuration, not code).

    Pass `overrides` only for values you want to deviate from the YAML defaults.
    Example:
        build_system_prompt()                            # all YAML defaults
        build_system_prompt(role="legal assistant")      # override one var
        build_system_prompt("analyst", field="finance")  # different prompt + var
    '''
    return get_prompt_registry().render(prompt_name, **overrides)


def build_user_message(question: str) -> str:
    '''
    Wrap the user's question with the `reminder` prompt.

    The reminder is appended AFTER the question so it lands at the very end of
    the context — the highest-retention position — countering "Lost in the
    Middle". It lives in its own reminder.yaml, applied at runtime rather than
    baked into the system prompt.
    '''
    reminder = get_prompt_registry().render("reminder")
    return f"{question}\n{reminder}"


# ---------------------------------------------------------------------------
# ReAct loop — Think → Act → Observe → Repeat
# ---------------------------------------------------------------------------
def execute_tool(tool_call: dict) -> str:
    '''
    Safely execute a single tool call. Delegates to ToolWrapper.call(), which
    performs lookup → Pydantic validation → execution and returns descriptive
    error strings instead of raising (the LLM reads this as an observation,
    so it must be human-readable, never a raw stack trace).
    '''
    return ToolWrapper.call(tool_call["name"], tool_call["args"])


def react_loop(llm, messages: list, max_iterations: int = 10, verbose: bool = False) -> str:
    '''
    Run the ReAct loop until the LLM produces a final answer (no tool calls)
    or until max_iterations is reached.

    Each iteration:
      1. invoke the LLM (Think)
      2. if no tool_calls → return the final answer
      3. otherwise execute every requested tool (Act) and append the results
         as ToolMessages (Observe), then loop again.

    `max_iterations` is the safety net against infinite loops and runaway cost.
    Best practice: 5-10 for normal tasks, 15-20 for complex ones.

    With `verbose=True`, each tool call and its result are printed — useful for
    watching the agent's reasoning in the interactive console.
    '''
    for _ in range(max_iterations):
        response: AIMessage = llm.invoke(messages)
        messages.append(response)

        # No tools requested → this is the final answer.
        if not response.tool_calls:
            return response.content

        # Act + Observe: run each requested tool, feed results back to the LLM.
        for tool_call in response.tool_calls:
            if verbose:
                print(f"  [tool] {tool_call['name']}({tool_call['args']})")
            result = execute_tool(tool_call)
            if verbose:
                print(f"  [result] {result}")
            messages.append(
                ToolMessage(content=str(result), tool_call_id=tool_call["id"])
            )

    raise RuntimeError("Max iterations reached without a final answer")


def ask(question: str, **prompt_overrides) -> str:
    '''
    High-level entry point: build the system prompt + tool-bound LLM, then run
    the full ReAct loop. This is the recommended way to query the agent.
    '''
    llm = build_llm()
    messages = [
        SystemMessage(content=build_system_prompt(**prompt_overrides)),
        HumanMessage(content=build_user_message(question)),
    ]
    return react_loop(llm, messages)


# ---------------------------------------------------------------------------
# One-shot chat (Phase 3) — kept as a simpler reference; handles AT MOST one
# round of tool use. For multi-step reasoning use ask() / react_loop().
# ---------------------------------------------------------------------------
def chat(question: str, system_prompt: str | None = None) -> str:
    '''Single-turn QA: one LLM call, one round of tools, one final LLM call.'''
    if system_prompt is None:
        system_prompt = build_system_prompt()

    llm = build_llm()
    messages = [
        SystemMessage(content=system_prompt),
        HumanMessage(content=build_user_message(question)),
    ]

    response: AIMessage = llm.invoke(messages)
    if not response.tool_calls:
        return response.content

    messages.append(response)
    for tool_call in response.tool_calls:
        result = ToolWrapper.call(tool_call["name"], tool_call["args"])
        messages.append(ToolMessage(content=str(result), tool_call_id=tool_call["id"]))

    final: AIMessage = llm.invoke(messages)
    return final.content


# ---------------------------------------------------------------------------
# Interactive console — a minimal multi-turn chat with the agent
# ---------------------------------------------------------------------------
def interactive() -> None:
    '''
    Minimal REPL to converse with the agent over multiple turns.

    Conversation history is kept across turns (the LLM sees the whole thread),
    and the reminder is re-applied to every user message. Tool calls are shown
    inline so you can watch the Think → Act → Observe steps.

    Commands: 'exit' / 'quit' to leave, 'reset' to clear the history.
    '''
    print("QA Agent — chat with tools. Commands: 'exit'/'quit', 'reset'.")
    llm = build_llm()
    system = SystemMessage(content=build_system_prompt())
    messages: list = [system]

    while True:
        try:
            user_input = input("\nYou> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nBye.")
            break

        if not user_input:
            continue
        if user_input.lower() in {"exit", "quit"}:
            print("Bye.")
            break
        if user_input.lower() == "reset":
            messages = [system]
            print("(history cleared)")
            continue

        messages.append(HumanMessage(content=build_user_message(user_input)))
        try:
            answer = react_loop(llm, messages, verbose=True)
        except Exception as e:
            print(f"[error] {e}")
            continue
        print(f"\nAgent> {answer}")


if __name__ == "__main__":
    interactive()
