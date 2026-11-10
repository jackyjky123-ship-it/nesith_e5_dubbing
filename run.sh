#!/usr/bin/env bash
# KhmerDub application launcher
set -e
PROJECT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
cd "$PROJECT_DIR"
exec "$PROJECT_DIR/venv/bin/python3" "$PROJECT_DIR/app.py" "$@"

