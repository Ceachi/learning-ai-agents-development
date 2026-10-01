# ─────────────────────────────────────────────────────────
# Part 3 · Inference — sklearn classifier + LLM fallback
#   • detect_intent_sklearn  → load once, predict + confidence, fall back
#       to the LLM when confidence < 0.7 (ambiguous cases).
#   • detect_intent_llm      → the LLM-based approach, 3 categories
#       (search / extract / summarize) over our llm.chat facade.
#
# Both have the same signature so they can be compared 1:1 in benchmark.py.
# ─────────────────────────────────────────────────────────
from pathlib import Path

import joblib

from llm import chat

MODEL_PATH = Path(__file__).parent / "intent_classifier.joblib"

CONFIDENCE_THRESHOLD = 0.7   # below this → rely on the LLM (ambiguous cases)

# Load the classifier once at import time.
# If the model does not exist yet, run `python -m part3_intent.train`.
_classifier = joblib.load(MODEL_PATH) if MODEL_PATH.exists() else None


# ── ML: sklearn classifier (replaces the LLM call) ───────────────────
def detect_intent_sklearn(query: str) -> str:
    """Detect the intent with the TF-IDF + LogisticRegression classifier.

    If confidence < 0.7 → fall back to the LLM (ambiguous cases). Returns
    only the label, for a 1:1 comparison with the LLM.
    """
    if _classifier is None:
        raise RuntimeError(
            "Model not found. Run first: python -m part3_intent.train"
        )
    intent = _classifier.predict([query])[0]
    confidence = max(_classifier.predict_proba([query])[0])

    if confidence < CONFIDENCE_THRESHOLD:   # not confident → ask the LLM
        return detect_intent_llm(query)
    return intent


def predict_with_confidence(query: str) -> tuple[str, float]:
    """Variant that also returns the confidence (useful for debugging)."""
    intent = _classifier.predict([query])[0]
    confidence = max(_classifier.predict_proba([query])[0])
    return intent, confidence


# ── LLM: the expensive approach ──────────────────────────────────────
def detect_intent_llm(query: str) -> str:
    """Classify the intent with a single LLM call (3 categories)."""
    prompt = f"""Classify the intent of the query into one of these categories:
- search: find/look up information or documents
- extract: pull structured data out of a document
- summarize: summarize/synthesize content

Query: {query}
Reply with the category only (a single word)."""

    response = chat(prompt, max_tokens=10)
    return response.strip().lower()
