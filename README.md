# Envoy Proxy POC - AWS Infrastructure

This repository contains Pulumi infrastructure-as-code projects for deploying an AWS EKS cluster with Envoy proxy for WebSocket application testing.

## Project Structure

The infrastructure is organized into separate Pulumi projects, each implementing a specific requirement section:

```
envoy-proxy-poc/
├── requirements.txt                 # Complete requirements document
├── pulumi-venv/                    # Shared Python virtual environment
├── 02-aws-networking/              # Section 2: VPC, Subnets, Security Groups
│   ├── __main__.py
│   ├── Pulumi.yaml
│   ├── Pulumi.dev.yaml
│   ├── README.md
│   └── verify.sh
└── 03-eks-cluster/                 # Section 3: EKS Cluster and Node Group
    ├── __main__.py
    ├── Pulumi.yaml
    ├── Pulumi.dev.yaml
    ├── README.md
    ├── setup.sh
    └── verify.sh
```

## Prerequisites

Before deploying any infrastructure, ensure you have:

1. **AWS CLI** configured with the `avive-cfndev-k8s` profile
2. **Pulumi CLI** installed
3. **Python 3.x** installed
4. **kubectl** installed (for EKS cluster verification)

## Quick Start

### 1. Set up the shared Python environment

```bash
# Create shared virtual environment (if not exists)
python3 -m venv pulumi-venv

# Activate the environment
source pulumi-venv/bin/activate

# Install required packages
pip install pulumi>=3.0.0 pulumi-aws>=6.0.0
```

### 2. Configure AWS credentials

```bash
# Test AWS profile
aws sts get-caller-identity --profile avive-cfndev-k8s
```

### 3. Deploy infrastructure in order

#### Step 1: Deploy Networking Infrastructure

```bash
cd 02-aws-networking

# Run setup (handles stack initialization)
./setup.sh    # If this script exists, otherwise:

# Manual setup:
pulumi stack init dev
pulumi login s3://cfndev-envoy-proxy-poc-pulumi-state

# Deploy
source ../pulumi-venv/bin/activate
export AWS_PROFILE=avive-cfndev-k8s
pulumi up

# Verify deployment
./verify.sh
```

#### Step 2: Deploy EKS Cluster

```bash
cd ../03-eks-cluster

# Run setup (handles stack initialization and dependency checks)
./setup.sh

# Deploy
pulumi up

# Verify deployment
./verify.sh
```

## Configuration

Each project uses Pulumi configuration to avoid hardcoded values. Key configurations:

### Global Settings
- **AWS Region**: `us-west-2`
- **AWS Profile**: `avive-cfndev-k8s`
- **KMS Key**: `pulumi-envoy-proxy-iac`
- **S3 Backend**: `s3://cfndev-envoy-proxy-poc-pulumi-state`

### Networking (02-aws-networking)
- **VPC Name**: `envoy-vpc`
- **VPC CIDR**: `172.245.0.0/16`
- **Project Name**: `envoy-poc`

### EKS Cluster (03-eks-cluster)
- **Cluster Name**: `envoy-poc`
- **Kubernetes Version**: `1.33`
- **Node Instance Type**: `t3.medium`
- **Node Capacity**: 2 desired (2-4 min-max)

## Stack Dependencies

The projects use Pulumi stack references to share resources:

```
02-aws-networking (base)
    ↓
03-eks-cluster (depends on networking)
```

## Verification

Each project includes a verification script:

```bash
# In each project directory
./verify.sh
```

## Outputs and Stack References

### Networking Stack Outputs
- VPC ID and CIDR
- Public and private subnet IDs  
- Security group IDs
- NAT gateway and internet gateway IDs

### EKS Cluster Stack Outputs
- Cluster name, ARN, and endpoint
- Certificate authority data
- Node group information
- OIDC issuer URL
- kubeconfig update command

## Troubleshooting

### Common Issues

1. **Stack not found**: Run the setup script in each project directory
2. **AWS credentials**: Ensure `avive-cfndev-k8s` profile is configured
3. **Backend access**: Verify S3 bucket permissions
4. **Dependency errors**: Deploy networking stack before EKS cluster

### Useful Commands

```bash
# Check stack status
pulumi stack ls

# View stack outputs
pulumi stack output

# Preview changes
pulumi preview

# Deploy changes
pulumi up

# Destroy resources (careful!)
pulumi destroy
```

## Security

- All resources use appropriate security groups
- KMS encryption for EKS secrets
- Private subnets for worker nodes
- IAM roles with least privilege

## Cost Considerations

The infrastructure creates:
- EKS cluster (control plane charges)
- 2x t3.medium EC2 instances (worker nodes)
- 2x NAT gateways
- ALB (when deployed in later sections)

Estimated cost: ~$150-200/month for POC usage.

## Next Steps

After deploying the base infrastructure:
1. Deploy ECR repositories (Section 4)
2. Deploy applications (Sections 5, 6, 7)
3. Run end-to-end verification tests

## Support

For issues:
1. Check the verification scripts output
2. Review Pulumi logs: `pulumi logs`
3. Check AWS CloudFormation console for detailed errors
4. Verify AWS credentials and permissions
