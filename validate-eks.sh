#!/bin/bash

# Validate EKS Cluster Deployment
# This script validates that the EKS cluster has been deployed successfully

set -e

# Source configuration
source config.sh

echo "=== EKS Cluster Validation ==="
echo "Cluster Name: $CLUSTER_NAME"
echo "AWS Profile: $AWS_PROFILE"
echo "AWS Region: $AWS_REGION"
echo ""

# Check if cluster exists and is active
echo "1. Checking EKS cluster status..."
CLUSTER_STATUS=$(aws eks describe-cluster \
    --name "$CLUSTER_NAME" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    --query 'cluster.status' \
    --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$CLUSTER_STATUS" = "ACTIVE" ]; then
    echo "✅ EKS cluster '$CLUSTER_NAME' is ACTIVE"
else
    echo "❌ EKS cluster '$CLUSTER_NAME' status: $CLUSTER_STATUS"
    exit 1
fi

# Check node group status
echo ""
echo "2. Checking node group status..."
NODE_GROUP_STATUS=$(aws eks describe-nodegroup \
    --cluster-name "$CLUSTER_NAME" \
    --nodegroup-name "envoy-poc-workers" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    --query 'nodegroup.status' \
    --output text 2>/dev/null || echo "NOT_FOUND")

if [ "$NODE_GROUP_STATUS" = "ACTIVE" ]; then
    echo "✅ Node group 'envoy-poc-workers' is ACTIVE"
else
    echo "❌ Node group 'envoy-poc-workers' status: $NODE_GROUP_STATUS"
    exit 1
fi

# Check node group capacity
echo ""
echo "3. Checking node group capacity..."
NODE_DETAILS=$(aws eks describe-nodegroup \
    --cluster-name "$CLUSTER_NAME" \
    --nodegroup-name "envoy-poc-workers" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    --query 'nodegroup.scalingConfig' \
    --output table)

echo "Node Group Scaling Configuration:"
echo "$NODE_DETAILS"

# Update kubeconfig and test cluster connectivity
echo ""
echo "4. Updating kubeconfig and testing cluster connectivity..."
aws eks update-kubeconfig \
    --name "$CLUSTER_NAME" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE"

echo ""
echo "5. Testing kubectl connectivity..."
if kubectl cluster-info >/dev/null 2>&1; then
    echo "✅ kubectl can connect to the cluster"
    kubectl cluster-info
else
    echo "❌ kubectl cannot connect to the cluster"
    exit 1
fi

# Check nodes
echo ""
echo "6. Checking cluster nodes..."
NODE_COUNT=$(kubectl get nodes --no-headers 2>/dev/null | wc -l)
if [ "$NODE_COUNT" -ge 2 ]; then
    echo "✅ Found $NODE_COUNT worker nodes (expected: 2+)"
    kubectl get nodes
else
    echo "❌ Found $NODE_COUNT worker nodes (expected: 2+)"
    kubectl get nodes
    exit 1
fi

# Check system pods
echo ""
echo "7. Checking system pods..."
SYSTEM_PODS_READY=$(kubectl get pods -n kube-system --no-headers 2>/dev/null | grep -c "Running" || echo "0")
SYSTEM_PODS_TOTAL=$(kubectl get pods -n kube-system --no-headers 2>/dev/null | wc -l || echo "0")

echo "System pods: $SYSTEM_PODS_READY/$SYSTEM_PODS_TOTAL running"
if [ "$SYSTEM_PODS_READY" -eq "$SYSTEM_PODS_TOTAL" ] && [ "$SYSTEM_PODS_TOTAL" -gt 0 ]; then
    echo "✅ All system pods are running"
else
    echo "⚠️  Some system pods may not be ready yet"
    kubectl get pods -n kube-system
fi

# Check addons
echo ""
echo "8. Checking EKS addons..."
ADDONS=$(aws eks list-addons \
    --cluster-name "$CLUSTER_NAME" \
    --region "$AWS_REGION" \
    --profile "$AWS_PROFILE" \
    --query 'addons' \
    --output table)

echo "Installed addons:"
echo "$ADDONS"

echo ""
echo "=== EKS Cluster Validation Complete ==="
echo "✅ EKS cluster '$CLUSTER_NAME' is ready for workload deployment"
echo ""
echo "Next steps:"
echo "- Deploy container registries (ECR repositories)"
echo "- Build and push application containers"
echo "- Deploy Envoy proxy and applications to the cluster"
