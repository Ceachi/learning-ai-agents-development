# ─────────────────────────────────────────────────────────
# Part 1 · Demo — conversation memory that survives restarts
#
# Run (needs Postgres up + ANTHROPIC_API_KEY):
#   docker-compose up -d
#   python -m part1_memory.demo
# ─────────────────────────────────────────────────────────
from part1_memory.agent import chat, memory

SESSION_ID = "andrei-demo"


def main():
    print("=" * 60)
    print("PART 1 · CONVERSATION MEMORY (LangGraph + PostgreSQL)")
    print("=" * 60)
    print(f"session_id = {SESSION_ID!r}\n")

    # ── Turn 1 — give the agent a fact to remember ───────────────────
    print("→ Turn 1: 'My name is Andrei and I work with invoices.'")
    reply1 = chat(SESSION_ID, "My name is Andrei and I work with invoices.")
    print(f"   assistant: {reply1}\n")

    # ── Turn 2 — same session: does it remember? ─────────────────────
    print("→ Turn 2: 'What is my name?'")
    reply2 = chat(SESSION_ID, "What is my name?")
    print(f"   assistant: {reply2}\n")

    # ── Proof the history really lives in PostgreSQL ─────────────────
    print("-" * 60)
    print("Messages persisted in PostgreSQL for this session_id:")
    print("-" * 60)
    stored = memory.load_messages(SESSION_ID)
    for i, m in enumerate(stored, 1):
        print(f"  {i}. [{m['role']:>9}] {m['content']}")
    print(f"\n✓ {len(stored)} messages in DB.")

    # ── The restart point ────────────────────────────────────────────
    # Memory lives in the database, NOT in process RAM. If you stop this
    # script and run it again, Turn 1 above will already see the messages
    # from THIS run — the conversation grows across process restarts.
    # (That is exactly what "long-term storage in PostgreSQL" means: kill
    # the app, restart, history is still there.)
    print(
        "\nℹ️  Run the script again: the new Turn 1 will already see the\n"
        "   messages from this run — memory survives a process restart,\n"
        "   because it lives in PostgreSQL, not in RAM."
    )


if __name__ == "__main__":
    main()
