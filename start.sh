#!/usr/bin/env bash
# CBETAfetch 2.0 Startup Script
set -e
cd "$(dirname "$0")"

if [ ! -d ".venv" ]; then
    echo "Creating virtual environment for CBETAfetch 2.0..."
    python3 -m venv .venv
    UV_CACHE_DIR=/tmp/uv-cache uv pip install --python ./.venv/bin/python fastapi uvicorn pydantic aiofiles httpx pytest pytest-asyncio requests
fi

echo "Verifying CBETAfetch 2.0 Core Subsystems..."
./.venv/bin/python verify.py

echo "Starting CBETAfetch 2.0 Server..."
./.venv/bin/python run.py "$@"
