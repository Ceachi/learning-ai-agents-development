# ─────────────────────────────────────────────────────────
# Part 3 · Benchmark — LLM vs sklearn on latency, cost, accuracy
#
# Run (needs model trained + ANTHROPIC_API_KEY for the LLM rows):
#   python -m part3_intent.train       # once
#   python -m part3_intent.benchmark
# ─────────────────────────────────────────────────────────
import time

from part3_intent.classifier import detect_intent_llm, predict_with_confidence

# ── Cost per call (USD) ──────────────────────────────────────────────
COST_LLM = 0.02         # ~$0.02 per LLM call
COST_SKLEARN = 0.00001  # practically free (local CPU only)


# ── Test set — distinct from training_data, mix of all 3 labels ──────
test_set: list[tuple[str, str]] = [
    ("search for the invoices from june", "search"),
    ("find the contract with Orange", "search"),
    ("show the unpaid documents", "search"),
    ("extract the total amount from the invoice", "extract"),
    ("pull the VAT id from the contract", "extract"),
    ("parse the table from the PDF", "extract"),
    ("summarize the quarterly report", "summarize"),
    ("give me a summary of the new contract", "summarize"),
    ("synthesize the 3 offers", "summarize"),
    ("give me a summary of the invoice", "summarize"),
]


# ── Latency helper ───────────────────────────────────────────────────
def benchmark(func, *args, iterations=100):
    """Measure the average latency."""
    times = []
    for _ in range(iterations):
        start = time.perf_counter()
        func(*args)
        times.append(time.perf_counter() - start)
    return {
        "avg_ms": sum(times) / len(times) * 1000,
        "min_ms": min(times) * 1000,
        "max_ms": max(times) * 1000,
    }


# For the benchmark we use the PURE classifier prediction (no LLM fallback) —
# we want to measure the ML path exactly, not an occasional LLM call.
def detect_intent_sklearn_pure(query: str) -> str:
    return predict_with_confidence(query)[0]


def accuracy(predict_fn) -> float:
    correct = sum(1 for q, gold in test_set if predict_fn(q) == gold)
    return correct / len(test_set)


def main():
    print("=" * 60)
    print("PART 3 · BENCHMARK: LLM vs sklearn (intent classifier)")
    print("=" * 60)
    print(f"Test set: {len(test_set)} examples (search / extract / summarize)\n")

    sample = test_set[0][0]   # one query used for the latency measurement

    # ── Latency ──────────────────────────────────────────────────────
    print("Measuring latency...")
    # LLM: few iterations, each call costs money.
    llm_stats = benchmark(detect_intent_llm, sample, iterations=10)
    # sklearn: free, so we can iterate a lot.
    ml_stats = benchmark(detect_intent_sklearn_pure, sample, iterations=100)

    # ── Accuracy ─────────────────────────────────────────────────────
    print("Measuring accuracy...\n")
    acc_llm = accuracy(detect_intent_llm)
    acc_ml = accuracy(detect_intent_sklearn_pure)

    # ── Comparison table ─────────────────────────────────────────────
    print(f"{'Method':<10}{'avg_ms':>12}{'$/1000 calls':>16}{'accuracy':>12}")
    print("-" * 50)
    print(f"{'LLM':<10}{llm_stats['avg_ms']:>11.0f}{COST_LLM * 1000:>15.2f}${acc_llm:>11.0%}")
    print(f"{'sklearn':<10}{ml_stats['avg_ms']:>11.1f}{COST_SKLEARN * 1000:>15.2f}${acc_ml:>11.0%}")
    print("-" * 50)

    # ── Takeaway with numbers ────────────────────────────────────────
    speedup = llm_stats["avg_ms"] / ml_stats["avg_ms"] if ml_stats["avg_ms"] else 0
    cost_ratio = COST_LLM / COST_SKLEARN
    print(f"\n⚡ sklearn is ~{speedup:.0f}× faster and ~{cost_ratio:.0f}× cheaper.")
    print("   For intent detection (a simple, repetitive problem), a classifier")
    print("   trained once replaces the LLM call at a fraction of the cost.")


if __name__ == "__main__":
    main()
