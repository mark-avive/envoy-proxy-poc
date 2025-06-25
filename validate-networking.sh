#!/bin/bash

# Validation script for Envoy Proxy POC AWS Networking Infrastructure
# This script validates that all networking components are properly deployed

set -e

# Source configuration
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPT_DIR/config.sh"

echo "🔍 Validating Envoy Proxy POC AWS Networking Infrastructure..."

# Check if AWS CLI is available and configured
if ! command -v aws &> /dev/null; then
    echo "❌ AWS CLI is not installed"
    exit 1
fi

if ! check_aws_profile; then
    exit 1
fi

# Check if Pulumi is available
if ! command -v pulumi &> /dev/null; then
    echo "❌ Pulumi CLI is not installed"
    exit 1
fi

echo "✅ Prerequisites check passed"

# Get stack outputs
echo "📊 Retrieving stack outputs..."

VPC_ID=$(pulumi stack output vpc_id 2>/dev/null || echo "")
PUBLIC_SUBNETS=$(pulumi stack output public_subnet_ids 2>/dev/null || echo "")
PRIVATE_SUBNETS=$(pulumi stack output private_subnet_ids 2>/dev/null || echo "")

if [[ -z "$VPC_ID" ]]; then
    echo "❌ Could not retrieve VPC ID from Pulumi stack"
    exit 1
fi

echo "✅ Stack outputs retrieved successfully"
echo "   VPC ID: $VPC_ID"

# Validate VPC
echo "🔍 Validating VPC..."
VPC_STATE=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --profile "$AWS_PROFILE" --query 'Vpcs[0].State' --output text)
if [[ "$VPC_STATE" != "available" ]]; then
    echo "❌ VPC is not in available state: $VPC_STATE"
    exit 1
fi

VPC_CIDR=$(aws ec2 describe-vpcs --vpc-ids "$VPC_ID" --profile "$AWS_PROFILE" --query 'Vpcs[0].CidrBlock' --output text)
if [[ "$VPC_CIDR" != "172.245.0.0/16" ]]; then
    echo "❌ VPC CIDR mismatch. Expected: 172.245.0.0/16, Got: $VPC_CIDR"
    exit 1
fi

echo "✅ VPC validation passed"

# Validate subnets
echo "🔍 Validating subnets..."
SUBNET_COUNT=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --profile "$AWS_PROFILE" --query 'length(Subnets)')
if [[ "$SUBNET_COUNT" -ne 4 ]]; then
    echo "❌ Expected 4 subnets, found $SUBNET_COUNT"
    exit 1
fi

# Check public subnets
PUBLIC_SUBNET_COUNT=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:kubernetes.io/role/elb,Values=1" --profile "$AWS_PROFILE" --query 'length(Subnets)')
if [[ "$PUBLIC_SUBNET_COUNT" -ne 2 ]]; then
    echo "❌ Expected 2 public subnets, found $PUBLIC_SUBNET_COUNT"
    exit 1
fi

# Check private subnets
PRIVATE_SUBNET_COUNT=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" "Name=tag:kubernetes.io/role/internal-elb,Values=1" --profile "$AWS_PROFILE" --query 'length(Subnets)')
if [[ "$PRIVATE_SUBNET_COUNT" -ne 2 ]]; then
    echo "❌ Expected 2 private subnets, found $PRIVATE_SUBNET_COUNT"
    exit 1
fi

echo "✅ Subnet validation passed"

# Validate Internet Gateway
echo "🔍 Validating Internet Gateway..."
IGW_COUNT=$(aws ec2 describe-internet-gateways --filters "Name=attachment.vpc-id,Values=$VPC_ID" --profile "$AWS_PROFILE" --query 'length(InternetGateways)')
if [[ "$IGW_COUNT" -ne 1 ]]; then
    echo "❌ Expected 1 Internet Gateway, found $IGW_COUNT"
    exit 1
fi

echo "✅ Internet Gateway validation passed"

# Validate NAT Gateways
echo "🔍 Validating NAT Gateways..."
NAT_COUNT=$(aws ec2 describe-nat-gateways --filter "Name=vpc-id,Values=$VPC_ID" --profile "$AWS_PROFILE" --query 'length(NatGateways[?State==`available`])')
if [[ "$NAT_COUNT" -ne 2 ]]; then
    echo "❌ Expected 2 available NAT Gateways, found $NAT_COUNT"
    exit 1
fi

echo "✅ NAT Gateway validation passed"

# Validate Security Groups
echo "🔍 Validating Security Groups..."
SG_COUNT=$(aws ec2 describe-security-groups --filters "Name=vpc-id,Values=$VPC_ID" "Name=group-name,Values=envoy-poc-*" --profile "$AWS_PROFILE" --query 'length(SecurityGroups)')
if [[ "$SG_COUNT" -ne 4 ]]; then
    echo "❌ Expected 4 custom security groups, found $SG_COUNT"
    exit 1
fi

echo "✅ Security Group validation passed"

# Validate Route Tables
echo "🔍 Validating Route Tables..."
RT_COUNT=$(aws ec2 describe-route-tables --filters "Name=vpc-id,Values=$VPC_ID" --profile "$AWS_PROFILE" --query 'length(RouteTables)')
if [[ "$RT_COUNT" -lt 4 ]]; then  # 1 default + 1 public + 2 private
    echo "❌ Expected at least 4 route tables, found $RT_COUNT"
    exit 1
fi

echo "✅ Route Table validation passed"

# Validate Availability Zones
echo "🔍 Validating Availability Zone distribution..."
AZ_COUNT=$(aws ec2 describe-subnets --filters "Name=vpc-id,Values=$VPC_ID" --profile "$AWS_PROFILE" --query 'length(Subnets[].AvailabilityZone | unique(@))')
if [[ "$AZ_COUNT" -ne 2 ]]; then
    echo "❌ Expected subnets in 2 Availability Zones, found $AZ_COUNT"
    exit 1
fi

echo "✅ Availability Zone validation passed"

echo ""
echo "🎉 All networking infrastructure validation checks passed!"
echo ""
echo "Summary:"
echo "✅ VPC: $VPC_ID (172.245.0.0/16)"
echo "✅ Subnets: 4 total (2 public, 2 private)"
echo "✅ Internet Gateway: 1"
echo "✅ NAT Gateways: 2"
echo "✅ Security Groups: 4 custom"
echo "✅ Route Tables: $RT_COUNT total"
echo "✅ Availability Zones: 2"
echo ""
echo "The networking infrastructure is ready for EKS cluster deployment!"
