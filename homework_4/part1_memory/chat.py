# ─────────────────────────────────────────────────────────
# Part 1 · Interactive chat — talk to the agent yourself
#
# Same persistent memory as the demo: everything you type is stored in
# PostgreSQL under a session_id, so the conversation survives restarts.
#
# Run (needs Postgres up + ANTHROPIC_API_KEY):
#   python -m part1_memory.chat                # default session "interactive"
#   python -m part1_memory.chat my-session     # pick / resume a session id
#
# Commands inside the chat:
#   /history   show all messages stored for this session
#   /exit      quit (the conversation stays in the DB)
# ─────────────────────────────────────────────────────────
import sys

from part1_memory.agent import chat, memory


def main():
    # session_id from the command line, or a default you can resume later.
    session_id = sys.argv[1] if len(sys.argv) > 1 else "interactive"

    print("=" * 60)
    print("PART 1 · INTERACTIVE CHAT (memory persisted in PostgreSQL)")
    print("=" * 60)
    print(f"session_id = {session_id!r}")
    print("Type your message. Commands: /history  /exit\n")

    # Show how many messages are already remembered for this session.
    existing = memory.load_messages(session_id)
    if existing:
        print(f"({len(existing)} earlier messages loaded for this session)\n")

    while True:
        try:
            user_input = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break

        if not user_input:
            continue

        if user_input in ("/exit", "/quit"):
            print("bye.")
            break

        if user_input == "/history":
            stored = memory.load_messages(session_id)
            print("-" * 60)
            for i, m in enumerate(stored, 1):
                print(f"  {i}. [{m['role']:>9}] {m['content']}")
            print(f"-- {len(stored)} messages in DB --\n")
            continue

        # Normal turn: the agent loads history, replies, and saves both messages.
        reply = chat(session_id, user_input)
        print(f"bot> {reply}\n")


if __name__ == "__main__":
    main()
