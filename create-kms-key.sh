#!/bin/bash

# Script to create the required KMS key for Pulumi secrets encryption
# Run this script if the KMS key doesn't exist yet

set -e

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "🔐 Creating KMS key for Pulumi secrets encryption..."

# Check if AWS CLI is configured with the required profile
if ! check_aws_profile; then
    exit 1
fi

# Check if the key already exists
if check_kms_key; then
    echo "✅ KMS key '$KMS_KEY_ALIAS' already exists"
    exit 0
fi

echo "🆕 Creating new KMS key..."

# Create the KMS key
KEY_ID=$(aws kms create-key \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --description "$KMS_KEY_DESCRIPTION" \
    --key-usage ENCRYPT_DECRYPT \
    --key-spec SYMMETRIC_DEFAULT \
    --origin AWS_KMS \
    --tags $PROJECT_TAGS \
    --query 'KeyMetadata.KeyId' \
    --output text)

echo "✅ KMS key created with ID: $KEY_ID"

# Create the alias
aws kms create-alias \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" \
    --alias-name "$KMS_KEY_ALIAS" \
    --target-key-id "$KEY_ID"

echo "✅ KMS key alias '$KMS_KEY_ALIAS' created"

# Verify the key is accessible
if check_kms_key; then
    echo "✅ KMS key verification successful"
else
    echo "❌ KMS key verification failed"
    exit 1
fi

echo ""
echo "🎉 KMS key setup complete!"
echo ""
echo "Key details:"
echo "- Key ID: $KEY_ID"
echo "- Alias: $KMS_KEY_ALIAS"
echo "- Region: $AWS_REGION"
echo "- Purpose: Pulumi secrets encryption"
echo ""
echo "You can now run the setup script: ./setup.sh"
