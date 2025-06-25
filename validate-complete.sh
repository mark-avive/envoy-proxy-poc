#!/bin/bash

# Complete Infrastructure Validation Script
# Tests both networking and EKS cluster components

set -e

# Source configuration
source config.sh

echo "======================================="
echo "  ENVOY PROXY POC - INFRASTRUCTURE VALIDATION"
echo "======================================="
echo "Project: $PROJECT_NAME"
echo "Cluster: $CLUSTER_NAME"
echo "AWS Profile: $AWS_PROFILE"
echo "AWS Region: $AWS_REGION"
echo ""

# Function to print section headers
print_section() {
    echo ""
    echo "--- $1 ---"
}

# Function to check command availability
check_command() {
    if ! command -v "$1" &> /dev/null; then
        echo "❌ Command '$1' is not available. Please install it."
        exit 1
    fi
}

print_section "CHECKING PREREQUISITES"
echo "Checking required tools..."
check_command aws
check_command kubectl
check_command pulumi
echo "✅ All required tools are available"

# Check AWS profile
echo ""
echo "Checking AWS profile access..."
if aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
    CALLER_IDENTITY=$(aws sts get-caller-identity --profile "$AWS_PROFILE" --output table)
    echo "✅ AWS profile '$AWS_PROFILE' is accessible"
    echo "$CALLER_IDENTITY"
else
    echo "❌ AWS CLI profile '$AWS_PROFILE' is not configured or not accessible."
    exit 1
fi

print_section "NETWORKING VALIDATION"
echo "Running networking validation..."
if ./validate-networking.sh; then
    echo "✅ Networking validation passed"
else
    echo "❌ Networking validation failed"
    exit 1
fi

print_section "EKS CLUSTER VALIDATION"
echo "Running EKS cluster validation..."
if ./validate-eks.sh; then
    echo "✅ EKS cluster validation passed"
else
    echo "❌ EKS cluster validation failed"
    exit 1
fi

print_section "PULUMI STACK STATUS"
echo "Checking Pulumi stack status..."
pulumi stack --stack "$PULUMI_STACK_NAME" 2>/dev/null || {
    echo "❌ Pulumi stack '$PULUMI_STACK_NAME' not found or not accessible"
    exit 1
}

echo "Current Pulumi stack info:"
pulumi stack --stack "$PULUMI_STACK_NAME"

echo ""
echo "Recent deployments:"
pulumi history --stack "$PULUMI_STACK_NAME" | head -10

print_section "RESOURCE SUMMARY"
echo "Getting infrastructure resource summary..."

# VPC Info
VPC_ID=$(aws ec2 describe-vpcs \
    --filters "Name=tag:Name,Values=envoy-vpc" \
    --query 'Vpcs[0].VpcId' \
    --output text \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" 2>/dev/null || echo "NOT_FOUND")

echo "VPC ID: $VPC_ID"

# Subnet counts
PUBLIC_SUBNETS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=*public*" \
    --query 'length(Subnets)' \
    --output text \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" 2>/dev/null || echo "0")

PRIVATE_SUBNETS=$(aws ec2 describe-subnets \
    --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:Name,Values=*private*" \
    --query 'length(Subnets)' \
    --output text \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" 2>/dev/null || echo "0")

echo "Public Subnets: $PUBLIC_SUBNETS"
echo "Private Subnets: $PRIVATE_SUBNETS"

# EKS Cluster info
CLUSTER_STATUS=$(aws eks describe-cluster \
    --name "$CLUSTER_NAME" \
    --query 'cluster.status' \
    --output text \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" 2>/dev/null || echo "NOT_FOUND")

CLUSTER_VERSION=$(aws eks describe-cluster \
    --name "$CLUSTER_NAME" \
    --query 'cluster.version' \
    --output text \
    --profile "$AWS_PROFILE" \
    --region "$AWS_REGION" 2>/dev/null || echo "NOT_FOUND")

echo "EKS Cluster Status: $CLUSTER_STATUS"
echo "EKS Kubernetes Version: $CLUSTER_VERSION"

# Node count
NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l || echo "0")
echo "Worker Nodes: $NODE_COUNT"

print_section "COST ESTIMATION"
echo "Estimated monthly costs (us-west-2):"
echo "- EKS Control Plane: ~\$73/month"
echo "- EC2 Instances (2x t3.medium): ~\$60/month"
echo "- EBS Storage (2x 20GB): ~\$4/month"
echo "- NAT Gateways (2x): ~\$90/month"
echo "- CloudWatch Logs: ~\$5/month"
echo "- Data Transfer: Variable"
echo "Total Estimated: ~\$232/month"

print_section "NEXT STEPS"
echo "Infrastructure deployment complete! ✅"
echo ""
echo "Ready for next phases:"
echo "1. Container Registries (Section 4) - Create ECR repositories"
echo "2. Server Application (Section 5) - Build WebSocket server"
echo "3. Envoy Proxy Setup (Section 6) - Deploy Envoy reverse proxy"
echo "4. Client Application (Section 7) - Deploy test client"
echo "5. Load Balancer Setup - Deploy AWS Load Balancer Controller"
echo ""
echo "kubectl access configured. Try these commands:"
echo "  kubectl get nodes"
echo "  kubectl get pods -A"
echo "  kubectl cluster-info"

print_section "CLEANUP INSTRUCTIONS"
echo "To destroy the infrastructure when done:"
echo "  pulumi destroy --stack $PULUMI_STACK_NAME"
echo ""
echo "⚠️  Remember to check for any orphaned resources after cleanup!"

echo ""
echo "======================================="
echo "  VALIDATION COMPLETE - SUCCESS! ✅"
echo "======================================="
