# ─────────────────────────────────────────────────────────
# Part 2 · Prompt Caching (Anthropic) — cache_control: ephemeral
#
# The provider caches the STATIC prefix (system prompt + fixed document).
# Call 1 WRITES the cache (cache_creation > 0).
# Call 2 READS the cache (cache_read > 0) → input at 0.1x = ~90% cheaper.
#
# ⚠️ Sonnet 4.x needs a prefix of AT LEAST ~2048 tokens to activate the
#    cache, otherwise cache_creation stays 0 (no error). The document below
#    is sized to cross the threshold (a repeated paragraph).
# ─────────────────────────────────────────────────────────
from llm import chat


# Large static prefix (>2048 tokens). In practice this would be a document /
# contract. We repeat a paragraph to cross the threshold without inventing
# five pages of text.
DOCUMENT = (
    "Service agreement between TechCorp Ltd and the supplier ACME. "
    "Terms include: delivery within 30 days, a 0.1% per-day late penalty, "
    "19% VAT applied to the net value, payment within 15 days of the "
    "invoice. Confidentiality and force majeure clauses apply. "
) * 60   # ~ crosses 2048 tokens

# system = [small unchanged prefix] + [large document marked for caching].
SYSTEM_BLOCKS = [
    {"type": "text", "text": "You are a contract analyst."},
    {
        "type": "text",
        "text": DOCUMENT,
        "cache_control": {"type": "ephemeral"},   # ← marks the prefix to cache
    },
]


def ask(question: str):
    """Send a question with the cached static prefix. Returns (text, usage).

    `usage` carries cache_creation_input_tokens / cache_read_input_tokens /
    input_tokens — exactly the numbers we need to MEASURE the saving.
    """
    return chat(question, system=SYSTEM_BLOCKS, return_usage=True)
