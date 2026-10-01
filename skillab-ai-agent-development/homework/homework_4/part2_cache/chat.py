# ─────────────────────────────────────────────────────────
# Part 2 · Interactive prompt-cache chat — ask the cached document yourself
#
# Every question reuses the same large static prefix (system + document),
# marked cache_control: ephemeral. Watch the usage line on each turn:
#   - first question  → cache MISS (cache_creation > 0)
#   - next questions  → cache HIT  (cache_read > 0, billed at 0.1x)
# The cache lives ~5 minutes (TTL); after that the next question is a MISS again.
#
# Run (needs ANTHROPIC_API_KEY):
#   python -m part2_cache.chat
#
# Commands:  /exit   quit
# ─────────────────────────────────────────────────────────
import time

from part2_cache.prompt_cache import ask


def main():
    print("=" * 60)
    print("PART 2 · INTERACTIVE PROMPT CACHE")
    print("=" * 60)
    print("Ask questions about the cached contract document.")
    print("Watch MISS vs HIT in the usage line. Commands: /exit\n")

    while True:
        try:
            question = input("you> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\nbye.")
            break

        if not question:
            continue
        if question in ("/exit", "/quit"):
            print("bye.")
            break

        t0 = time.perf_counter()
        text, u = ask(question)
        latency = (time.perf_counter() - t0) * 1000

        status = "HIT " if u["cache_read_input_tokens"] else "MISS"
        print(f"bot> {text}")
        print(f"     [{status}] cache_creation={u['cache_creation_input_tokens']}  "
              f"cache_read={u['cache_read_input_tokens']}  "
              f"fresh_input={u['input_tokens']}  "
              f"latency={latency:.0f}ms\n")


if __name__ == "__main__":
    main()
