#!/bin/bash
set -e

echo "Setting up Python virtual environment..."

# Remove existing venv if it exists
if [ -d ".venv" ]; then
    echo "Removing existing .venv directory..."
    rm -rf .venv
fi

# Create new virtual environment and install dependencies with uv
echo "Creating virtual environment and installing dependencies with uv..."
uv sync --all-extras

# Install pre-commit hooks
echo "Installing pre-commit hooks..."
uv run pre-commit install

# Install cspell globally for spell checking
echo "Installing cspell for spell checking..."
if command -v npm &> /dev/null; then
    npm install -g cspell@latest
    echo "cspell installed successfully"
else
    echo "Warning: npm not found. Install Node.js to use spell checking."
    echo "You can install cspell later with: npm install -g cspell@latest"
fi

echo "Setup complete!"
