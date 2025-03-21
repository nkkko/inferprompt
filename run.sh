#!/bin/bash

# Check if uv is installed
if ! command -v uv &> /dev/null; then
    echo "uv not found. Installing uv from astral.sh..."
    curl -LsSf https://astral.sh/uv/install.sh | sh
    export PATH="$HOME/.cargo/bin:$PATH"
fi

# Check if virtual environment exists
if [ ! -d ".venv" ]; then
    echo "Creating virtual environment with uv..."
    uv venv .venv
    echo "Installing dependencies with uv..."
    uv pip install -r requirements.txt
else
    echo "Using existing virtual environment..."
fi

# Activate the virtual environment
source .venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    cp .env.example .env
    echo "Please edit the .env file with your API keys before running the server."
    exit 1
fi

# Run the FastAPI server
echo "Starting InferPrompt API server..."
uvicorn app.main:app --reload
