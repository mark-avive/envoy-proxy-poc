# EKS Cluster Infrastructure - Envoy Proxy POC

This Pulumi project implements requirement section 3 from the Envoy Proxy POC requirements document.

## Overview

This project creates an AWS EKS cluster with the following specifications:

- **Cluster Name**: `envoy-poc`
- **Kubernetes Version**: 1.33
- **Node Group Configuration**:
  - Instance Type: `t3.medium`
  - Desired Capacity: 2 nodes
  - Min Capacity: 2 nodes  
  - Max Capacity: 4 nodes
  - AMI Type: `AL2_x86_64` (Amazon Linux 2)
- **API Server Endpoints**: Both public and private endpoints enabled
- **Control Plane Logging**: Enabled for `api`, `audit`, `authenticator`, and `scheduler` logs

## Dependencies

This project depends on the `02-aws-networking` stack and references the following resources:
- VPC ID
- Private subnet IDs (for worker nodes)
- Public subnet IDs (for load balancers)
- EKS cluster security group
- Worker node security group

## Resources Created

### IAM Roles and Policies
- EKS Cluster Service Role with required policies
- EKS Node Group Service Role with required policies

### EKS Resources
- EKS Cluster with encryption at rest
- EKS Managed Node Group
- CloudWatch Log Group for control plane logs

## Deployment

Before deploying this stack, ensure the networking stack (`02-aws-networking`) is already deployed.

### Prerequisites
- AWS CLI configured with `avive-cfndev-k8s` profile
- Pulumi CLI installed  
- Python virtual environment set up (shared at `../pulumi-venv`)
- Networking stack (`02-aws-networking`) deployed

### Initialize Stack (if not already done)

If this is the first time setting up the stack:

```bash
# Navigate to the project directory
cd 03-eks-cluster

# Run automated setup (default stack name 'dev')
./setup.sh

# Or specify a different stack name
./setup.sh prod

# Manual initialization (if needed)
pulumi stack init dev  # or your preferred stack name
pulumi login s3://cfndev-envoy-proxy-poc-pulumi-state
pulumi config set aws:region us-west-2
pulumi config set aws:profile avive-cfndev-k8s
```

### Deploy Infrastructure

```bash
# Activate the shared virtual environment
source ../pulumi-venv/bin/activate

# Set AWS profile
export AWS_PROFILE=avive-cfndev-k8s

# Preview the deployment
pulumi preview

# Deploy the infrastructure
pulumi up
```

## Outputs

The stack exports the following outputs for use by other stacks:
- `cluster_name`: The EKS cluster name
- `cluster_arn`: The EKS cluster ARN
- `cluster_endpoint`: The EKS cluster API endpoint
- `cluster_version`: The Kubernetes version
- `cluster_certificate_authority_data`: Certificate authority data for kubectl
- `cluster_security_group_id`: Additional security group created by EKS
- `node_group_arn`: The node group ARN
- `cluster_oidc_issuer_url`: OIDC issuer URL for service accounts
- `kubeconfig_update_command`: Command to update local kubeconfig

## Post-Deployment Verification

After successful deployment, verify the cluster:

```bash
# Update kubeconfig
aws eks update-kubeconfig --name envoy-poc --region us-west-2 --profile avive-cfndev-k8s

# Verify cluster info
kubectl cluster-info

# Check nodes
kubectl get nodes

# Verify node group
kubectl get nodes -o wide
```

## Configuration

All configuration values are managed through Pulumi config. See `Pulumi.dev.yaml` for current settings.

Key configuration values:
- `cluster_name`: EKS cluster name
- `kubernetes_version`: Kubernetes version to deploy
- `node_instance_type`: EC2 instance type for worker nodes
- `node_desired_capacity`: Desired number of worker nodes
- `node_min_capacity`: Minimum number of worker nodes
- `node_max_capacity`: Maximum number of worker nodes
- `networking_stack_name`: Name of the networking stack to reference
- `kms_key_alias`: KMS key alias for EKS encryption (default: alias/pulumi-envoy-proxy-iac)
