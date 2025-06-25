#!/bin/bash

# Centralized configuration for Envoy Proxy POC
# This file contains all shared configuration values used across scripts

# AWS Configuration
export AWS_PROFILE="avive-cfndev-k8s"
export AWS_REGION="us-west-2"

# KMS Configuration
export KMS_KEY_ALIAS="alias/pulumi-envoy-proxy-iac"
export KMS_KEY_DESCRIPTION="KMS key for Pulumi Envoy Proxy POC secrets encryption"

# Pulumi Configuration  
export PULUMI_STACK_NAME="cfndev"
export PULUMI_S3_BACKEND="s3://cfndev-envoy-proxy-poc-pulumi-state"

# Project Configuration
export PROJECT_NAME="envoy-proxy-poc"
export PROJECT_TAGS="TagKey=Project,TagValue=envoy-proxy-poc TagKey=Purpose,TagValue=pulumi-secrets TagKey=Environment,TagValue=poc"
export CLUSTER_NAME="envoy-poc"

# Derived values
export PULUMI_SECRETS_PROVIDER="awskms://${KMS_KEY_ALIAS}?region=${AWS_REGION}"

# Function to check if AWS CLI profile is accessible
check_aws_profile() {
    if ! aws sts get-caller-identity --profile "$AWS_PROFILE" &> /dev/null; then
        echo "❌ AWS CLI profile '$AWS_PROFILE' is not configured or not accessible."
        echo "   Please configure your AWS SSO profile first."
        return 1
    fi
    return 0
}

# Function to check if KMS key exists and is accessible
check_kms_key() {
    if ! aws kms describe-key --key-id "$KMS_KEY_ALIAS" --profile "$AWS_PROFILE" &> /dev/null; then
        return 1
    fi
    return 0
}

# Function to display current configuration
show_config() {
    echo "Current Configuration:"
    echo "- AWS Profile: $AWS_PROFILE"
    echo "- AWS Region: $AWS_REGION"
    echo "- KMS Key Alias: $KMS_KEY_ALIAS"
    echo "- Pulumi Stack: $PULUMI_STACK_NAME"
    echo "- S3 Backend: $PULUMI_S3_BACKEND"
}
