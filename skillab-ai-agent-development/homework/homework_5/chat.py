"""
chat.py — interactive REPL that talks to the HW5 MCP server using
Anthropic Claude as the reasoning loop.

Pattern (the standard agentic loop):

    read user input
      → Claude (with tools=mcp tools/list)
          → if tool_use → call MCP tool via fastmcp.Client
                            → feed tool_result back to Claude
                            → repeat
          → else: print Claude's text answer → loop

Commands inside the chat:
    /quit       — exit
    /tools      — list the MCP tools the server exposes
    /clear      — clear the conversation history
    /help       — show these commands

Pre-requisite: the MCP server must be running in another terminal:

    python mcp_server.py
"""

from __future__ import annotations

import asyncio
import json
import os

from dotenv import load_dotenv

import anthropic
from fastmcp import Client
from fastmcp.exceptions import ToolError


load_dotenv()


MCP_URL = "http://127.0.0.1:8000/mcp"
MODEL = os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929")
MAX_TOKENS = 2048


def mcp_tools_to_anthropic(tools) -> list[dict]:
    """Convert an MCP `tools/list` response into the Anthropic `tools` format."""
    return [
        {
            "name": t.name,
            "description": t.description,
            "input_schema": t.inputSchema,
        }
        for t in tools
    ]


async def call_mcp_tool(mcp_client: Client, name: str, args: dict) -> str:
    """Call one MCP tool and return its text content.

    Tool errors (e.g. guardrail blocks) are surfaced as plain strings so the
    chat keeps running — Claude will see the error and explain it to the user.
    """
    try:
        result = await mcp_client.call_tool(name, args)
        return result.content[0].text if result.content else "(empty result)"
    except ToolError as e:
        return f"⚠ Tool error from MCP server: {e}"


async def chat_loop() -> None:
    client = anthropic.Anthropic()

    async with Client(MCP_URL) as mcp_client:
        # Fetch the tool catalog once at startup.
        tools_obj = await mcp_client.list_tools()
        anthropic_tools = mcp_tools_to_anthropic(tools_obj)

        print(f"\n💬 Connected to {MCP_URL}")
        print(f"📋 Tools available: {', '.join(t['name'] for t in anthropic_tools)}")
        print("Type your question (or /help). Press Ctrl-D to quit.\n")

        # Conversation memory (kept across turns in a single session)
        messages: list[dict] = []

        while True:
            try:
                user_input = input("you ▸ ").strip()
            except (EOFError, KeyboardInterrupt):
                print("\nBye 👋")
                break

            if not user_input:
                continue

            # Local commands (do NOT reach the LLM)
            if user_input in {"/quit", "/exit"}:
                print("Bye 👋")
                break
            if user_input == "/help":
                print("  /tools  /clear  /quit  /help")
                continue
            if user_input == "/tools":
                for t in anthropic_tools:
                    first = (t["description"] or "").splitlines()[0]
                    print(f"  • {t['name']}: {first}")
                continue
            if user_input == "/clear":
                messages.clear()
                print("(history cleared)")
                continue

            messages.append({"role": "user", "content": user_input})

            # Agentic loop: keep calling Claude until it stops requesting tools.
            while True:
                resp = client.messages.create(
                    model=MODEL,
                    max_tokens=MAX_TOKENS,
                    tools=anthropic_tools,
                    messages=messages,
                )

                tool_uses = [b for b in resp.content if b.type == "tool_use"]

                if not tool_uses:
                    # No more tool calls — Claude has its final answer.
                    final = "".join(b.text for b in resp.content if b.type == "text")
                    print(f"\nbot ◂ {final}\n")
                    messages.append({"role": "assistant", "content": resp.content})
                    break

                # Record Claude's message (with tool_use blocks) BEFORE executing,
                # so the next turn has the right history shape.
                messages.append({"role": "assistant", "content": resp.content})

                # Execute every requested tool through the MCP server.
                tool_results = []
                for tu in tool_uses:
                    args_pretty = json.dumps(tu.input, ensure_ascii=False)
                    print(f"  → [tool] {tu.name}({args_pretty})")
                    output = await call_mcp_tool(mcp_client, tu.name, tu.input)
                    preview = output.splitlines()[0][:200]
                    suffix = "…" if len(output) > len(preview) else ""
                    print(f"    ← {preview}{suffix}")
                    tool_results.append({
                        "type": "tool_result",
                        "tool_use_id": tu.id,
                        "content": output,
                    })

                # Feed the tool results back into the conversation.
                messages.append({"role": "user", "content": tool_results})


if __name__ == "__main__":
    asyncio.run(chat_loop())
