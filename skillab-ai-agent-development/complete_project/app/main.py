"""
Document Analyst - Entrypoint pentru chat Q&A.

Usage:
    python -m app.main
    python -m app.main --provider anthropic
    python -m app.main --intent rag  # forțează RAG
"""
import argparse
import logging
import sys

from app.agents import Intent
from app.chat import ChatSession
from app.llm import get_llm

logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


def run_interactive(
    provider: str | None = None,
    model: str | None = None,
    intent: Intent | None = None,
):
    """
    Rulează sesiunea interactivă de chat.

    Args:
        provider: LLM provider (anthropic, google, ollama)
        model: Model specific
        intent: Forțează intent (rag sau sql)
    """
    llm = get_llm(provider=provider, model=model)
    session = ChatSession(llm=llm)

    print("\n" + "=" * 60)
    print("Document Analyst - SEAP Public Procurement Assistant")
    print("=" * 60)
    print(f"Provider: {llm.name} | Model: {llm.model}")
    if intent:
        print(f"Intent mode: {intent} (forced)")
    else:
        print("Intent mode: auto (classifier)")
    print("=" * 60)
    print("Comenzi: /quit, /clear, /rag, /sql")
    print("=" * 60 + "\n")

    while True:
        try:
            question = input("Tu: ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nLa revedere!")
            break

        if not question:
            continue

        # Commands
        if question.startswith("/"):
            cmd = question.lower()
            if cmd in ("/quit", "/exit", "/q"):
                print("La revedere!")
                break
            elif cmd == "/clear":
                session.clear_history()
                print("[Istoric șters]\n")
                continue
            elif cmd == "/rag":
                intent = "rag"
                print("[Mode: RAG]\n")
                continue
            elif cmd == "/sql":
                intent = "sql"
                print("[Mode: SQL]\n")
                continue
            elif cmd == "/auto":
                intent = None
                print("[Mode: Auto]\n")
                continue
            else:
                print(f"[Comandă necunoscută: {cmd}]\n")
                continue

        # Ask
        try:
            response = session.ask(question, intent=intent)
            print(f"\nAsistent [{response.intent}]: {response.answer}\n")
        except Exception as e:
            logger.exception("Error processing question")
            print(f"\n[Eroare: {e}]\n")


def main():
    """CLI entrypoint."""
    parser = argparse.ArgumentParser(
        description="Document Analyst - SEAP Q&A Assistant",
    )
    parser.add_argument(
        "--provider",
        choices=["anthropic", "google", "ollama"],
        help="LLM provider",
    )
    parser.add_argument(
        "--model",
        help="Model name",
    )
    parser.add_argument(
        "--intent",
        choices=["rag", "sql"],
        help="Force intent (skip classifier)",
    )
    args = parser.parse_args()

    try:
        run_interactive(
            provider=args.provider,
            model=args.model,
            intent=args.intent,
        )
    except KeyboardInterrupt:
        print("\nÎntrerupt.")
        sys.exit(0)


if __name__ == "__main__":
    main()
