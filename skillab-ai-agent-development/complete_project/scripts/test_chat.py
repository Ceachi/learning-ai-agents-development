"""Test chat session."""
import rootutils
rootutils.setup_root(__file__, indicator="pyproject.toml", pythonpath=True)

from app.chat import ChatSession


def main():
    session = ChatSession()

    queries = [
        ("Ce este o licitație deschisă?", "rag"),        # auto → rag
        ("Câte achiziții avem în total?", "sql"),        # auto → sql
        ("Explică procedura", "rag"),                   # force rag
        ("Top 5 furnizori", "sql"),                     # force sql
    ]

    for q, intent in queries:
        print(f"\n>>> {q}")
        if intent:
            print(f"    [forced: {intent}]")

        resp = session.ask(q, intent=intent)
        print(f"    Intent: {resp.intent} | Status: {resp.status}")
        print(f"    {resp.answer[:200]}...")

    print(f"\n--- History: {len(session.history)} messages ---")


if __name__ == "__main__":
    main()
