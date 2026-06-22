# ─────────────────────────────────────────────────────────
# Part 2 · Demo — measure tokens saved + latency reduction
#
# The saving is MEASURED, not asserted: we print the real usage numbers
# (call 1 = MISS, call 2 = HIT) and the wall-clock time of each call.
#
# Run (needs ANTHROPIC_API_KEY):
#   python -m part2_cache.demo
# ─────────────────────────────────────────────────────────
import time

from part2_cache.prompt_cache import ask


def main():
    print("=" * 60)
    print("PART 2 · PROMPT CACHING (Anthropic)")
    print("=" * 60)
    print("Cached static prefix: 'You are a contract analyst.' + document.\n")

    # ── Call 1 — writes the cache (MISS) ─────────────────────────────
    print("→ Call 1 (cache MISS — writes the cache):")
    t0 = time.perf_counter()
    _, u1 = ask("What is the late-delivery penalty?")
    lat1 = (time.perf_counter() - t0) * 1000
    print(f"   cache_creation={u1['cache_creation_input_tokens']}  "
          f"cache_read={u1['cache_read_input_tokens']}  "
          f"fresh_input={u1['input_tokens']}  "
          f"latency={lat1:.0f}ms")

    # ── Call 2 — reads the cache (HIT) ───────────────────────────────
    print("\n→ Call 2 (cache HIT — reads the cache):")
    t0 = time.perf_counter()
    _, u2 = ask("What VAT rate is applied?")
    lat2 = (time.perf_counter() - t0) * 1000
    print(f"   cache_creation={u2['cache_creation_input_tokens']}  "
          f"cache_read={u2['cache_read_input_tokens']}  "
          f"fresh_input={u2['input_tokens']}  "
          f"latency={lat2:.0f}ms")

    # ── Token saving: cache_read costs 0.1x of normal input ──────────
    print("\n" + "-" * 60)
    cached = u2["cache_read_input_tokens"]
    if cached:
        saved = (1 - 0.1) * 100   # 0.1x price → 90% reduction on the cached part
        print(f"💰 {cached} tokens served from cache at 0.1x → ~{saved:.0f}% "
              f"reduction on the cached part of the input.")
    else:
        print("⚠️ cache_read=0 — prefix below the threshold (2048 tok on Sonnet "
              "4.x) or the cache expired (5 min TTL).")

    # ── Latency reduction ────────────────────────────────────────────
    if lat1 > 0:
        drop = (1 - lat2 / lat1) * 100
        print(f"⚡ Latency: call 1 {lat1:.0f}ms → call 2 {lat2:.0f}ms  "
              f"(~{drop:.0f}% faster on HIT).")


if __name__ == "__main__":
    main()
