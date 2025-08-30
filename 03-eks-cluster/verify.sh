#!/bin/bash

# EKS Cluster Verification Script for Envoy Proxy POC
# This script verifies the EKS cluster deployment

set -e

echo "=== EKS Cluster Verification Script ==="
echo "Date: $(date)"
echo

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m' # No Color

# Function to print status
print_status() {
    if [ $1 -eq 0 ]; then
        echo -e "${GREEN}✓${NC} $2"
    else
        echo -e "${RED}✗${NC} $2"
    fi
}

# Check if required tools are installed
echo "Checking required tools..."
command -v pulumi >/dev/null 2>&1
print_status $? "Pulumi CLI is installed"

command -v kubectl >/dev/null 2>&1
print_status $? "kubectl is installed"

command -v aws >/dev/null 2>&1
print_status $? "AWS CLI is installed"

echo

# Check Pulumi stack status
echo "Checking Pulumi stack status..."
STACK_STATUS=$(pulumi stack --show-name 2>/dev/null || echo "error")
if [ "$STACK_STATUS" != "error" ]; then
    print_status 0 "Pulumi stack is selected: $STACK_STATUS"
    
    # Get stack outputs
    echo
    echo "Getting stack outputs..."
    CLUSTER_NAME=$(pulumi stack output cluster_name 2>/dev/null || echo "")
    CLUSTER_ENDPOINT=$(pulumi stack output cluster_endpoint 2>/dev/null || echo "")
    
    if [ ! -z "$CLUSTER_NAME" ]; then
        print_status 0 "Cluster name: $CLUSTER_NAME"
    else
        print_status 1 "Could not retrieve cluster name from stack outputs"
    fi
    
    if [ ! -z "$CLUSTER_ENDPOINT" ]; then
        print_status 0 "Cluster endpoint available"
    else
        print_status 1 "Could not retrieve cluster endpoint from stack outputs"
    fi
else
    print_status 1 "Pulumi stack not found or not selected"
    echo -e "${YELLOW}Please run this script from the 03-eks-cluster directory${NC}"
    exit 1
fi

echo

# Update kubeconfig if cluster name is available
if [ ! -z "$CLUSTER_NAME" ]; then
    echo "Updating kubeconfig..."
    aws eks update-kubeconfig --name "$CLUSTER_NAME" --region us-west-2 --profile avive-cfndev-k8s >/dev/null 2>&1
    print_status $? "Updated kubeconfig for cluster: $CLUSTER_NAME"
    echo
fi

# Verify cluster connectivity
echo "Verifying cluster connectivity..."
kubectl cluster-info >/dev/null 2>&1
if [ $? -eq 0 ]; then
    print_status 0 "Successfully connected to EKS cluster"
    
    # Get cluster info
    echo
    echo "Cluster Information:"
    kubectl cluster-info
    echo
    
    # Check nodes
    echo "Checking worker nodes..."
    NODES=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
    if [ $NODES -gt 0 ]; then
        print_status 0 "Found $NODES worker node(s)"
        echo
        kubectl get nodes -o wide
    else
        print_status 1 "No worker nodes found"
    fi
    
    echo
    
    # Check node readiness
    echo "Checking node readiness..."
    READY_NODES=$(kubectl get nodes --no-headers 2>/dev/null | grep -c "Ready" || echo "0")
    if [ $READY_NODES -gt 0 ]; then
        print_status 0 "$READY_NODES node(s) are Ready"
    else
        print_status 1 "No nodes are in Ready state"
    fi
    
    echo
    
    # Check system pods
    echo "Checking system pods..."
    SYSTEM_PODS=$(kubectl get pods -n kube-system --no-headers 2>/dev/null | grep -c "Running" || echo "0")
    if [ $SYSTEM_PODS -gt 0 ]; then
        print_status 0 "$SYSTEM_PODS system pods are Running"
    else
        print_status 1 "System pods may not be ready"
    fi
    
else
    print_status 1 "Could not connect to EKS cluster"
    echo -e "${YELLOW}Make sure the cluster is deployed and AWS credentials are configured${NC}"
fi

echo
echo "=== Verification Complete ==="
