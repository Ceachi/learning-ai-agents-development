# ─────────────────────────────────────────────────────────
# Part 3 · Interactive intent classifier — type a query, see the intent
#
# Each line you type is classified by the sklearn model (instant, free):
# it prints the predicted intent + confidence. When confidence is below the
# threshold, the agent would fall back to the LLM (shown as a note).
#
# Run (needs the model trained; LLM compare needs ANTHROPIC_API_KEY):
#   python -m part3_intent.train      # once, if not done yet
#   python -m part3_intent.chat
#
# Commands:
#   /llm     toggle: also call the LLM and compare predictions
#   /exit    quit
# ─────────────────────────────────────────────────────────
from part3_intent.classifier import (
    CONFIDENCE_THRESHOLD,
    detect_intent_llm,
    predict_with_confidence,
)


def main():
    print("=" * 60)
    print("PART 3 · INTERACTIVE INTENT CLASSIFIER")
    print("=" * 60)
    print("Type a query → sklearn predicts the intent (search/extract/summarize).")
    print("Commands: /llm (toggle LLM comparison)  /exit\n")

    compare_llm = False

    while True:
        try:
            query = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break

        if not query:
            continue
        if query in ("/exit", "/quit"):
            print("bye.")
            break
        if query == "/llm":
            compare_llm = not compare_llm
            print(f"   LLM comparison: {'ON' if compare_llm else 'OFF'}\n")
            continue

        intent, confidence = predict_with_confidence(query)
        low = confidence < CONFIDENCE_THRESHOLD
        flag = "  (low confidence → would fall back to LLM)" if low else ""
        print(f"sklearn> {intent}  (confidence {confidence:.2f}){flag}")

        if compare_llm:
            print(f"llm>     {detect_intent_llm(query)}")
        print()


if __name__ == "__main__":
    main()
