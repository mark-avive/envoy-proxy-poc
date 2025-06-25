#!/bin/bash

# Simple script to display current project configuration
# Usage: ./show-config.sh

set -e

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "🔧 Envoy Proxy POC Configuration"
echo "================================"
echo ""
show_config
echo ""
echo "🔗 Configuration file: $SCRIPT_DIR/config.sh"
echo "📖 Documentation: $SCRIPT_DIR/CONFIG.md"
