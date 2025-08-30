#!/bin/bash

# EKS Cluster Stack Setup Script for Envoy Proxy POC
# This script initializes the Pulumi stack if not already done
#
# Usage: ./setup.sh [stack_name]
# Example: ./setup.sh dev
#          ./setup.sh prod
# Default stack name is 'dev' if not specified

set -e

echo "=== EKS Cluster Stack Setup ==="
echo "Date: $(date)"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

print_info() {
    echo -e "${BLUE}ℹ${NC} $1"
}

print_warning() {
    echo -e "${YELLOW}⚠${NC} $1"
}

# Check if we're in the right directory
if [ ! -f "Pulumi.yaml" ]; then
    echo -e "${RED}Error: This script must be run from the 03-eks-cluster directory${NC}"
    exit 1
fi

# Check if required tools are installed
echo "Checking prerequisites..."
command -v pulumi >/dev/null 2>&1
print_status $? "Pulumi CLI is installed"

command -v aws >/dev/null 2>&1
print_status $? "AWS CLI is installed"

# Check if virtual environment exists
if [ -d "../pulumi-venv" ]; then
    print_status 0 "Shared virtual environment found"
else
    print_status 1 "Shared virtual environment not found at ../pulumi-venv"
    echo -e "${YELLOW}Please create the shared virtual environment first${NC}"
    exit 1
fi

echo

# Check AWS profile
print_info "Checking AWS profile configuration..."
if aws sts get-caller-identity --profile avive-cfndev-k8s >/dev/null 2>&1; then
    print_status 0 "AWS profile 'avive-cfndev-k8s' is configured and working"
else
    print_status 1 "AWS profile 'avive-cfndev-k8s' is not configured or not working"
    echo -e "${YELLOW}Please configure your AWS credentials${NC}"
    exit 1
fi

echo

# Activate virtual environment
print_info "Activating shared virtual environment..."
source ../pulumi-venv/bin/activate
print_status $? "Virtual environment activated"

# Set environment variables
export AWS_PROFILE=avive-cfndev-k8s
export AWS_REGION=us-west-2

# Get stack name from user or use default
STACK_NAME=${1:-"dev"}
print_info "Using stack name: $STACK_NAME"

echo

# Check if stack exists
print_info "Checking stack status..."
STACK_EXISTS=$(pulumi stack ls --json 2>/dev/null | jq -r ".[] | select(.name==\"$STACK_NAME\") | .name" 2>/dev/null || echo "")

if [ "$STACK_EXISTS" = "$STACK_NAME" ]; then
    print_status 0 "Stack '$STACK_NAME' already exists"
    
    # Select the stack
    pulumi stack select $STACK_NAME >/dev/null 2>&1
    print_status $? "Stack '$STACK_NAME' selected"
else
    print_info "Stack '$STACK_NAME' does not exist, creating..."
    
    # Create the stack (show output to debug issues)
    print_info "Running: pulumi stack init $STACK_NAME"
    if pulumi stack init $STACK_NAME; then
        print_status 0 "Stack '$STACK_NAME' created"
    else
        print_status 1 "Failed to create stack '$STACK_NAME'"
        echo -e "${YELLOW}Try running manually: pulumi stack init $STACK_NAME${NC}"
        exit 1
    fi
fi

echo

# Check if backend is configured
print_info "Checking Pulumi backend configuration..."
BACKEND_URL=$(pulumi about --json 2>/dev/null | jq -r '.backend.url' 2>/dev/null || echo "")
if [[ "$BACKEND_URL" == *"s3://cfndev-envoy-proxy-poc-pulumi-state"* ]]; then
    print_status 0 "S3 backend already configured"
else
    print_info "Configuring S3 backend..."
    pulumi login s3://cfndev-envoy-proxy-poc-pulumi-state >/dev/null 2>&1
    print_status $? "S3 backend configured"
fi

echo

# Verify KMS key exists (use default if config not set yet)
print_info "Checking KMS key availability..."
# Try to get from config, fallback to default if not set or if stack is new
KMS_KEY_ALIAS=$(pulumi config get envoy-poc-eks-cluster:kms_key_alias 2>/dev/null || echo "alias/pulumi-envoy-proxy-iac")
print_info "Using KMS key alias: $KMS_KEY_ALIAS"

KMS_KEY_CHECK=$(aws kms describe-key --key-id "$KMS_KEY_ALIAS" --profile $AWS_PROFILE --region $AWS_REGION 2>/dev/null || echo "")
if [ ! -z "$KMS_KEY_CHECK" ]; then
    print_status 0 "KMS key '$KMS_KEY_ALIAS' is accessible"
    
    # Set the KMS key config if it's not already set (for new stacks)
    CURRENT_KMS_CONFIG=$(pulumi config get envoy-poc-eks-cluster:kms_key_alias 2>/dev/null || echo "")
    if [ -z "$CURRENT_KMS_CONFIG" ]; then
        print_info "Setting KMS key alias in stack configuration..."
        pulumi config set envoy-poc-eks-cluster:kms_key_alias "$KMS_KEY_ALIAS" >/dev/null 2>&1
        print_status $? "KMS key alias configured"
    fi
else
    print_status 1 "KMS key '$KMS_KEY_ALIAS' is not accessible"
    echo -e "${YELLOW}Please ensure the KMS key exists and you have access to it${NC}"
    print_info "You can check available KMS keys with:"
    echo "  aws kms list-aliases --profile $AWS_PROFILE --region $AWS_REGION"
    echo
    print_info "If you need to use a different KMS key, you can set it with:"
    echo "  pulumi config set envoy-poc-eks-cluster:kms_key_alias alias/your-key-name"
    exit 1
fi

echo

# Verify networking stack dependency
print_info "Checking networking stack dependency..."
NETWORKING_STACK_OUTPUT=$(pulumi stack output --stack 02-aws-networking/$STACK_NAME vpc_id 2>/dev/null || echo "")
if [ ! -z "$NETWORKING_STACK_OUTPUT" ]; then
    print_status 0 "Networking stack (02-aws-networking/$STACK_NAME) is deployed and accessible"
else
    print_status 1 "Networking stack (02-aws-networking/$STACK_NAME) is not deployed or not accessible"
    echo -e "${YELLOW}Please deploy the networking stack first:${NC}"
    echo "  cd ../02-aws-networking"
    echo "  ./setup.sh $STACK_NAME  # or pulumi stack init $STACK_NAME"
    echo "  pulumi up"
    exit 1
fi

echo

# Show current configuration
print_info "Current stack configuration:"
pulumi config

echo
echo -e "${GREEN}=== Setup Complete ===${NC}"
echo
echo "Next steps:"
echo "1. Review the configuration above"
echo "2. Run 'pulumi preview' to see planned changes"
echo "3. Run 'pulumi up' to deploy the EKS cluster"
echo
echo "Commands to run:"
echo -e "${BLUE}  pulumi preview${NC}"
echo -e "${BLUE}  pulumi up${NC}"
