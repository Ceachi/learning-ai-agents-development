#!/bin/bash
# Run the FastAPI backend server

cd "$(dirname "$0")/.."

echo "Starting FastAPI server on http://localhost:8000"
python -m uvicorn app.api.main:app --reload --host 0.0.0.0 --port 8000
