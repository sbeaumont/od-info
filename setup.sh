#!/bin/bash
# Set up OD Info: install uv if needed, sync dependencies, configure

set -e

if which uv &> /dev/null; then
    echo "uv is already installed."
else
    echo "Installing uv..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
fi

echo ""
echo "Installing dependencies..."
uv sync

echo ""
uv run python setup.py

echo ""
echo "Run ./odinfo.sh to start the application."