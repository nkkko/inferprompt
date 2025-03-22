#!/bin/bash

# Only recreate virtual environment if it doesn't exist or if force flag is set
if [ ! -d ".venv" ] || [ "$1" == "--force" ]; then
    # Remove existing virtual environment if it exists
    if [ -d ".venv" ]; then
        echo "Removing existing virtual environment..."
        rm -rf .venv
    fi

    # Check if uv is installed
    if ! command -v uv &> /dev/null; then
        echo "uv not found. Installing uv from astral.sh..."
        curl -LsSf https://astral.sh/uv/install.sh | sh
        export PATH="$HOME/.cargo/bin:$PATH"
    fi

    # Create a fresh virtual environment
    echo "Creating new virtual environment with uv..."
    uv venv .venv
    echo "Installing dependencies with uv..."
    uv pip install -r requirements.txt
else
    echo "Using existing virtual environment. Use --force to recreate it."
fi

# Activate the virtual environment
source .venv/bin/activate

# Check if .env file exists
if [ ! -f ".env" ]; then
    echo "Creating .env file from template..."
    if [ -f ".env.example" ]; then
        cp .env.example .env
        echo "Please edit the .env file with your API keys before running the server."
    else
        echo "ERROR: .env.example file not found. Please create a .env file manually."
    fi
    exit 1
fi

# Run the FastAPI server
echo "Starting InferPrompt API server..."
# Use port 8080 to avoid conflicts with other services
port=${PORT:-8080}
uvicorn app.main:app --reload --port $port
