# ─────────────────────────────────────────────────────────
# Part 1 · LangGraph Document Analyst with PostgreSQL memory
#
# The agent node loads conversation history from PostgreSQL on every turn,
# invokes the LLM with the full history + current user message, then saves
# both new messages back to PostgreSQL. Memory survives application restarts
# because it lives in the database, not in RAM (LOAD → INVOKE → SAVE).
# ─────────────────────────────────────────────────────────
import os
from pathlib import Path

import yaml
from dotenv import load_dotenv
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from langchain_anthropic import ChatAnthropic
from langchain_core.messages import AIMessage, HumanMessage, SystemMessage
from langgraph.graph import StateGraph, START, END, MessagesState

from part1_memory.schema import Base
from part1_memory.memory_manager import PersistentMemory

load_dotenv(override=True)


# ── DB setup ─────────────────────────────────────────────────────────
DATABASE_URL = os.getenv(
    "DATABASE_URL",
    "postgresql://skillab:skillab_dev@localhost:5432/skillab",
)

engine = create_engine(DATABASE_URL)
Base.metadata.create_all(engine)            # create tables on first run
session_factory = sessionmaker(bind=engine)

memory = PersistentMemory(session_factory, window=10)


# ── LLM + system prompt (loaded from YAML, as required by the format) ─
llm = ChatAnthropic(
    model=os.getenv("ANTHROPIC_MODEL", "claude-sonnet-4-5-20250929"),
    temperature=0,
)

_PROMPT_PATH = Path(__file__).parent.parent / "prompts" / "analyst_system.yaml"
SYSTEM_PROMPT = yaml.safe_load(_PROMPT_PATH.read_text())["prompt"]


# ── LangGraph state — extends MessagesState with the session_id ──────
class AnalystState(MessagesState):
    session_id: str


# ── Agent node — LOAD from DB → INVOKE LLM → SAVE to DB ──────────────
def agent_node(state: AnalystState) -> dict:
    session_id = state["session_id"]
    # The new user message is whatever the caller just put into the state.
    current_user_msg = state["messages"][-1]

    # 1. LOAD — pull the last N messages from PostgreSQL
    history = memory.load_messages(session_id)

    # Build the full message list: [System] + [DB history] + [current user]
    full_messages: list = [SystemMessage(content=SYSTEM_PROMPT)]
    for m in history:
        if m["role"] == "user":
            full_messages.append(HumanMessage(content=m["content"]))
        else:
            full_messages.append(AIMessage(content=m["content"]))
    full_messages.append(current_user_msg)

    # 2. INVOKE — single LLM call with the assembled context
    response = llm.invoke(full_messages)

    # 3. SAVE — persist user msg + assistant reply (each in its own transaction)
    memory.save_message(session_id, "user", current_user_msg.content)
    memory.save_message(session_id, "assistant", response.content)

    return {"messages": [response]}         # add_messages reducer appends it


# ── Build the graph ──────────────────────────────────────────────────
builder = StateGraph(AnalystState)
builder.add_node("agent", agent_node)
builder.add_edge(START, "agent")
builder.add_edge("agent", END)

graph = builder.compile()


# ── Convenience wrapper for callers ──────────────────────────────────
def chat(session_id: str, user_input: str) -> str:
    """Send one user message, get the assistant reply.

    State is short-lived (one invocation = one user turn), but the conversation
    is persisted via PersistentMemory, so subsequent calls with the same
    session_id see the full history.
    """
    out = graph.invoke({
        "session_id": session_id,
        "messages": [HumanMessage(content=user_input)],
    })
    return out["messages"][-1].content
