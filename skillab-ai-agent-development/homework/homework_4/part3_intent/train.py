# ─────────────────────────────────────────────────────────
# Part 3 · Train the intent classifier — TF-IDF + LogisticRegression
#
# Run once (from homework_4/):
#   python -m part3_intent.train
# Produces: part3_intent/intent_classifier.joblib
# ─────────────────────────────────────────────────────────
from pathlib import Path

import joblib
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.pipeline import Pipeline

from part3_intent.training_data import training_data

# Save next to this file → the path does not depend on the current directory.
MODEL_PATH = Path(__file__).parent / "intent_classifier.joblib"


def train() -> Pipeline:
    # Split texts and labels
    texts = [t[0] for t in training_data]
    labels = [t[1] for t in training_data]

    # Build the pipeline (TF-IDF on unigrams + bigrams → logistic regression)
    classifier = Pipeline([
        ("tfidf", TfidfVectorizer(ngram_range=(1, 2))),
        ("clf", LogisticRegression(max_iter=1000)),
    ])

    # Train
    classifier.fit(texts, labels)

    # Persist for production use
    joblib.dump(classifier, MODEL_PATH)
    return classifier


if __name__ == "__main__":
    clf = train()
    print(f"✓ Trained on {len(training_data)} examples, {len(set(l for _, l in training_data))} classes.")
    print(f"✓ Saved to {MODEL_PATH}")
    # Quick sanity check
    for q in ["find the invoice from may", "extract the VAT id", "summarize the contract"]:
        print(f"   {q!r:45} → {clf.predict([q])[0]}")
