#!/bin/bash
# start.sh -- Requirement 9: a startup script that simplifies running the
# whole project (backend + frontend) with one command.
#
# Usage:
#   ./start.sh
#
# Requires: server/venv already created with dependencies installed
# (see README for first-time setup), and either OPENAI_API_KEY or
# GEMINI_API_KEY set in server/.env or the current shell environment.

set -e

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo "=================================================="
echo "  Day 14 - Kids Educational Chatbot"
echo "  Brain Buster | Quick Fire | Ask & Explore"
echo "=================================================="

# --- Backend ---
echo ""
echo "[1/2] Starting backend (FastAPI) on http://127.0.0.1:8000 ..."
cd "$SCRIPT_DIR/server"

if [ ! -d "venv" ]; then
    echo "No venv found -- creating one and installing dependencies (first run only)..."
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt --quiet
else
    source venv/bin/activate
fi

uvicorn app.main:app --host 127.0.0.1 --port 8000 &
BACKEND_PID=$!

# Give the backend a moment to start before launching the frontend.
sleep 2

# --- Frontend ---
echo ""
echo "[2/2] Starting frontend (Vite) on http://127.0.0.1:5173 ..."
cd "$SCRIPT_DIR/client"

if [ ! -d "node_modules" ]; then
    echo "No node_modules found -- running npm install (first run only)..."
    npm install --silent
fi

# Ensure the backend is stopped if this script is interrupted (Ctrl+C).
trap "echo ''; echo 'Stopping backend (PID $BACKEND_PID)...'; kill $BACKEND_PID 2>/dev/null" EXIT

npm run dev
