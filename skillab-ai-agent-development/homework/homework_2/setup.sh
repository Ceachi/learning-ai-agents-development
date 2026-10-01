#!/usr/bin/env bash
#
# One-shot setup: start the database, run migrations, build the similarity index,
# and index the sample documents — so the agent is ready to answer questions.
#
# Assumes: your Python environment is active, dependencies are installed
# (pip install -r requirements.txt), and .env has a valid ANTHROPIC_API_KEY.
#
# Run from the homework_2/ folder:  bash setup.sh
#
set -euo pipefail
cd "$(dirname "$0")"

echo "[1/4] Starting PostgreSQL + pgvector (Docker)..."
docker compose up -d --wait

echo "[2/4] Applying database migrations..."
alembic upgrade head

echo "[3/4] Building the HNSW similarity index..."
python -m db.create_index

echo "[4/4] Indexing the sample documents..."
python -c "from pathlib import Path; from rag import index_documents; index_documents(sorted(str(p) for p in Path('samples').glob('*.txt')))"

echo
echo "Done. The agent is ready."
echo "Start chatting with:  python agent.py"
