# Homework 4 — Memory, Caching & Intent Classifier

Three independent optimizations applied to an agent:

1. **Conversation Memory** (LangGraph + PostgreSQL) — context that survives
   application restarts.
2. **Prompt Caching** (Anthropic `cache_control: ephemeral`) — puts the system
   prompt + fixed context in the cache; measures the tokens saved and the
   latency reduction.
3. **Intent Classifier** (scikit-learn TF-IDF + LogisticRegression) — replaces
   LLM-based intent detection; compares latency, cost, and accuracy against the
   LLM.

## Structure

```
homework_4/
├── llm.py                      # Anthropic facade (chat + usage)
├── docker-compose.yml          # PostgreSQL (pgvector/pg16) for long-term memory
├── .env.example                # ANTHROPIC_API_KEY + DATABASE_URL
├── requirements.txt
├── prompts/
│   └── analyst_system.yaml     # system prompt for the memory agent
├── part1_memory/               # Part 1 — persistent memory
│   ├── schema.py               #   SQLAlchemy models (Session, ChatMessage, Entity)
│   ├── memory_manager.py       #   Repository + unit_of_work + PersistentMemory
│   ├── agent.py                #   LangGraph node: LOAD → INVOKE → SAVE
│   └── demo.py
├── part2_cache/                # Part 2 — prompt caching
│   ├── prompt_cache.py         #   static prefix marked cache_control: ephemeral
│   └── demo.py
└── part3_intent/               # Part 3 — intent classifier
    ├── training_data.py        #   60 (query, label) examples × 3 categories
    ├── train.py                #   trains the TF-IDF + LogisticRegression pipeline
    ├── classifier.py           #   sklearn inference + LLM fallback
    └── benchmark.py            #   LLM vs sklearn: latency, cost, accuracy
```

## Setup

```bash
# 1. API key + config
cp .env.example .env          # edit ANTHROPIC_API_KEY

# 2. Dependencies
pip install -r requirements.txt

# 3. PostgreSQL for Part 1 (wait for the healthcheck)
docker-compose up -d
```

Run all commands below from the `homework_4/` directory.

## How to run each part

### Part 1 — Conversation Memory
```bash
python -m part1_memory.demo
```
Sends two messages in the same session ("My name is Andrei..." then "What is my
name?"), shows that turn 2 remembers turn 1, then prints the messages read
straight from PostgreSQL. **Run the script a second time** to see that the
history is still there — memory survives a process restart because it lives in
the database, not in RAM.

To talk to the agent yourself (interactive REPL, same persistent memory):
```bash
python -m part1_memory.chat                # default session "interactive"
python -m part1_memory.chat my-session     # pick / resume a session id
```
Type messages freely; `/history` shows what's stored for the session, `/exit`
quits. Re-running with the same session id resumes the conversation.

Example session — what to type and what to expect:

| You type | What to expect |
|----------|----------------|
| `My name is Andrei and I work with ACME invoices.` | acknowledges, remembers the name + ACME |
| `What is my name?` | "Your name is Andrei." |
| `Which supplier did I mention?` | "ACME" |
| `/history` | lists every message stored in PostgreSQL for this session |
| `/exit` | quits (the conversation stays in the DB) |

The key test: run the same command again, then ask `What is my name?` — it still
answers "Andrei", proving memory survived the restart (it lives in the DB).

### Part 2 — Prompt Caching
```bash
python -m part2_cache.demo
```
Makes two calls with the same static prefix (system + a >2048-token document).
Call 1 = cache MISS (`cache_creation > 0`), call 2 = cache HIT (`cache_read > 0`,
billed at 0.1x). Prints the real usage numbers and the latency of both calls →
~90% reduction on the cached part.

To ask the cached document yourself (interactive):
```bash
python -m part2_cache.chat
```
Type questions about the contract; each turn prints `[MISS]`/`[HIT]` plus the
token usage and latency. The first question writes the cache; the next ones
read it (`cache_read > 0`). The cache lives ~5 min (TTL), so after a pause the
next question is a MISS again. `/exit` quits.

The cached document is a service contract (30-day delivery, 0.1%/day late
penalty, 19% VAT, payment within 15 days, confidentiality + force majeure).
What to type and what to expect:

| You type | Answer | Cache line |
|----------|--------|------------|
| `What is the late penalty?` | "0.1% per day" | `[MISS]` first time — writes the cache |
| `What VAT rate applies?` | "19%" | `[HIT]` — `cache_read > 0` |
| `What is the payment deadline?` | "within 15 days of the invoice" | `[HIT]` |
| `Who are the parties?` | "TechCorp Ltd and ACME" | `[HIT]` |
| `What clauses apply?` | "confidentiality and force majeure" | `[HIT]` |

What matters is the cache line, not the answer text: after the first call the
large input is served from cache (`cache_read`), i.e. ~90% cheaper on input.

### Part 3 — Intent Classifier
```bash
python -m part3_intent.train       # once → saves the .joblib model
python -m part3_intent.benchmark   # the LLM vs sklearn comparison
```
`train.py` trains the classifier on the 60 examples. `benchmark.py` prints a
table with **average latency, $/1000 calls, and accuracy** for both methods on
a separate test set.

To classify your own queries (interactive):
```bash
python -m part3_intent.chat
```
Type any sentence → sklearn prints the predicted intent + confidence instantly.
`/llm` toggles a side-by-side LLM prediction for comparison; `/exit` quits.

What to type and what to expect:

| You type | Predicted intent | Confidence |
|----------|------------------|------------|
| `find the invoices from march` | `search` | high (≥0.7) |
| `where are the unpaid contracts` | `search` | may be low (<0.7) — still correct |
| `extract the data from the invoice` | `extract` | high |
| `pull the total amount from this file` | `extract` | high / medium |
| `summarize the monthly report` | `summarize` | high |
| `the techsoft document` (vague) | uncertain | low — the fall-back case |

How to read it: the predicted intent is the model's best guess; `confidence` is
how sure it is (max probability across the 3 classes). With only ~20 examples
per class, free-form queries often land below the 0.7 threshold — the chat flags
these as "would fall back to LLM". **A low-confidence but correct prediction is
expected here, not a bug** — type `/llm` and repeat the query to confirm sklearn
and the LLM usually agree. More training examples per class would raise
confidence (the course notes 50–100/class reaches ~95%).

## Numbers each part produces

| Part | The numbers |
|------|-------------|
| 1 · Memory | number of messages persisted in PostgreSQL after a restart |
| 2 · Cache | `cache_creation` vs `cache_read` tokens (~90% saving) + latency drop |
| 3 · Intent | latency, $/1000 calls, and accuracy for both LLM and sklearn (sklearn ~100× faster and far cheaper) |

## Implementation notes

- The three intent categories are `search` / `extract` / `summarize`.
- Persistent memory uses the `PersistentMemory` pattern (Repository + Unit of
  Work) called from the LangGraph node (LOAD → INVOKE → SAVE), **not** an
  in-RAM checkpointer — the requirement is long-term storage in PostgreSQL.
  `chat_messages` has a foreign key to `sessions`, so the parent session row is
  created (get-or-create) before any message is saved.
- The trained model (`intent_classifier.joblib`) is regenerated by `train.py`,
  so it is not committed to git.
```
