#!/bin/bash

# Setup script for Envoy Proxy POC Pulumi infrastructure
# This script initializes the Pulumi project with proper configuration

set -e

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "🚀 Setting up Envoy Proxy POC Pulumi infrastructure..."
echo ""
show_config
echo ""

# Check if Pulumi is installed
if ! command -v pulumi &> /dev/null; then
    echo "❌ Pulumi is not installed. Please install Pulumi CLI first."
    echo "   Visit: https://www.pulumi.com/docs/get-started/install/"
    exit 1
fi

# Check if AWS CLI is configured with the required profile
if ! check_aws_profile; then
    exit 1
fi

echo "✅ Prerequisites check passed"

# Create Python virtual environment if it doesn't exist
if [ ! -d "venv" ]; then
    echo "📦 Creating Python virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment and install dependencies
echo "📦 Installing Python dependencies..."
source venv/bin/activate
pip install --upgrade pip > /dev/null 2>&1
pip install -r requirements-pulumi.txt > /dev/null 2>&1

echo "🔧 Configuring Pulumi backend..."

# Login to S3 backend
pulumi login "$PULUMI_S3_BACKEND"

# Verify KMS key access
echo "🔐 Verifying KMS key access..."
if ! check_kms_key; then
    echo "❌ Cannot access KMS key '$KMS_KEY_ALIAS'."
    echo "   Please ensure the key exists and you have permissions to use it."
    echo "   You can create the key by running: ./create-kms-key.sh"
    exit 1
fi
echo "✅ KMS key access verified"

# Initialize stack with KMS encryption
echo "🆕 Creating Pulumi stack '$PULUMI_STACK_NAME' with KMS encryption..."
pulumi stack init "$PULUMI_STACK_NAME" --secrets-provider="$PULUMI_SECRETS_PROVIDER"

# Set AWS configuration
echo "⚙️  Configuring AWS settings..."
pulumi config set aws:profile "$AWS_PROFILE"
pulumi config set aws:region "$AWS_REGION"

echo ""
echo "✅ Setup complete!"
echo ""
echo "🎯 Next steps (Pulumi automatically uses the virtual environment):"
echo "   1. Preview infrastructure: pulumi preview"
echo "   2. Deploy infrastructure: pulumi up"
echo "   3. Validate networking: ./validate-networking.sh"
echo ""
echo "🧹 To destroy later: pulumi destroy"
