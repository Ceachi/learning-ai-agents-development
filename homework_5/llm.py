"""
llm.py — thin Anthropic client used by the LLM-as-Judge guardrail.

    from llm import chat
    print(chat("Hello"))                       # -> str
    print(chat([{"role": "user", "content": "Hi"}]))

Env:
    ANTHROPIC_API_KEY   required
    ANTHROPIC_MODEL     optional (default below)
"""

from __future__ import annotations
from dotenv import load_dotenv
import os
from typing import Union

import anthropic

load_dotenv(override=True)

DEFAULT_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")

_client: anthropic.Anthropic | None = None


def _get_client() -> anthropic.Anthropic:
    global _client
    if _client is None:
        _client = anthropic.Anthropic()  # reads ANTHROPIC_API_KEY from env
    return _client


Messages = list[dict]


def _normalize(prompt: Union[str, Messages]) -> Messages:
    if isinstance(prompt, str):
        return [{"role": "user", "content": prompt}]
    return prompt


def chat(
    prompt: Union[str, Messages],
    *,
    system: Union[str, list, None] = None,
    model: str = DEFAULT_MODEL,
    temperature: float = 0.0,
    max_tokens: int = 1024,
):
    """Send a prompt, get back text. Sync, blocking, one call."""
    client = _get_client()
    kwargs = dict(
        model=model,
        max_tokens=max_tokens,
        temperature=temperature,
        messages=_normalize(prompt),
    )
    if system is not None:
        kwargs["system"] = system

    resp = client.messages.create(**kwargs)
    return resp.content[0].text


if __name__ == "__main__":
    print(chat("Say 'homework 5 ready' and nothing else."))
