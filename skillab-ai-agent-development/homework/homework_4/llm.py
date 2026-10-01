"""
llm.py — single import used by all demos.

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
    return_usage: bool = False,
):
    """Send a prompt, get back text. Sync, blocking, one call.

    With return_usage=True, also returns a dict with cache_read /
    cache_creation token counts — used by the prompt caching demo.
    """
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
    text = resp.content[0].text

    if return_usage:
        u = resp.usage
        usage = {
            "input_tokens": u.input_tokens,
            "output_tokens": u.output_tokens,
            "cache_creation_input_tokens": getattr(u, "cache_creation_input_tokens", 0) or 0,
            "cache_read_input_tokens": getattr(u, "cache_read_input_tokens", 0) or 0,
        }
        return text, usage

    return text


if __name__ == "__main__":
    print(chat("Say 'homework 4 ready' and nothing else."))
