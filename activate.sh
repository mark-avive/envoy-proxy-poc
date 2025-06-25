#!/bin/bash

# Simple script to show project status and available commands
# Pulumi automatically activates the virtual environment as specified in Pulumi.yaml

set -e

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

# Check if venv exists
if [ ! -d "venv" ]; then
    echo "❌ Virtual environment not found. Please run ./setup.sh first."
    exit 1
fi

echo "✅ $PROJECT_NAME ready (Pulumi auto-activates venv)"
echo ""
show_config
echo ""
echo "🎯 Available commands:"
echo "   - pulumi preview    # Preview changes (auto-activates venv)"
echo "   - pulumi up         # Deploy infrastructure (auto-activates venv)"
echo "   - pulumi destroy    # Destroy infrastructure (auto-activates venv)"
echo ""
