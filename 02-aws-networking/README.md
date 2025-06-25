# AWS Networking Infrastructure - Envoy Proxy POC

This Pulumi project implements the AWS networking infrastructure for the Envoy Proxy POC as specified in **Requirement Section 2**.

## Overview

This project creates a complete AWS networking foundation including:
- VPC with DNS support
- Public and private subnets across multiple availability zones
- Internet Gateway and NAT Gateways for internet connectivity
- Route tables with appropriate routing
- Security groups for EKS, ALB, and Envoy services

## Architecture

### VPC Configuration
- **Name**: `envoy-vpc`
- **CIDR**: `172.245.0.0/16`
- **DNS Hostnames**: Enabled
- **DNS Support**: Enabled

### Subnets
- **Public Subnets**: 2 subnets in different AZs (172.245.1.0/24, 172.245.2.0/24)
  - For AWS ALB and NAT Gateways
  - Auto-assign public IPs enabled
- **Private Subnets**: 2 subnets in different AZs (172.245.10.0/24, 172.245.11.0/24)
  - For EKS worker nodes and internal services

### Internet Connectivity
- **Internet Gateway**: Provides internet access for public subnets
- **NAT Gateways**: 2 NAT Gateways (one per public subnet) for private subnet internet egress
- **Elastic IPs**: 2 EIPs for NAT Gateway public addresses

### Security Groups
1. **EKS Cluster Security Group**: Communication between EKS control plane and worker nodes
2. **Worker Node Security Group**: 
   - Allows ingress from EKS cluster security group
   - Allows egress to AWS services and internet
   - Allows inter-worker node communication
3. **ALB Security Group**: Allows HTTP (port 80) ingress from internet
4. **Envoy Service Security Group**: Allows ingress from ALB security group

## Configuration

The project uses Pulumi configuration for all configurable values:

```bash
# View current configuration
pulumi config

# Key configurations:
# - vpc_name: "envoy-vpc"
# - vpc_cidr: "172.245.0.0/16"  
# - project_name: "envoy-poc"
# - aws:region: "us-west-2"
# - aws:profile: "avive-cfndev-k8s"
```

## Usage

### Prerequisites
- AWS CLI configured with `avive-cfndev-k8s` profile
- Pulumi CLI installed
- Python virtual environment set up

### Deploy Infrastructure

```bash
# Activate the shared virtual environment
source ../pulumi-venv/bin/activate

# Set AWS profile
export AWS_PROFILE=avive-cfndev-k8s

# Preview changes
pulumi preview

# Deploy infrastructure
pulumi up
```

### Verify Deployment

```bash
# Check stack outputs
pulumi stack output

# View resources in AWS Console
# - VPC: envoy-vpc
# - Subnets: envoy-poc-public/private-subnet-1/2
# - Security Groups: envoy-poc-*-sg
```

## Outputs

This stack exports the following outputs for use by other Pulumi stacks:

- `vpc_id`: VPC ID
- `vpc_cidr`: VPC CIDR block
- `public_subnet_ids`: Array of public subnet IDs
- `private_subnet_ids`: Array of private subnet IDs
- `public_subnet_1_id`, `public_subnet_2_id`: Individual public subnet IDs
- `private_subnet_1_id`, `private_subnet_2_id`: Individual private subnet IDs
- `internet_gateway_id`: Internet Gateway ID
- `nat_gateway_1_id`, `nat_gateway_2_id`: NAT Gateway IDs
- `eks_cluster_sg_id`: EKS Cluster Security Group ID
- `worker_node_sg_id`: Worker Node Security Group ID
- `alb_sg_id`: ALB Security Group ID
- `envoy_service_sg_id`: Envoy Service Security Group ID
- `availability_zones`: Available AWS availability zones

## Stack References

Other Pulumi stacks can reference these outputs using stack references:

```python
import pulumi

# Reference this stack's outputs
networking_stack = pulumi.StackReference("envoy-poc-aws-networking/dev")
vpc_id = networking_stack.get_output("vpc_id")
private_subnets = networking_stack.get_output("private_subnet_ids")
```

## Compliance

This implementation follows all requirements from **Section 2: AWS Networking**:
- ✅ New VPC with specified name and CIDR
- ✅ 2 public subnets in different AZs for ALB and NAT Gateways
- ✅ 2 private subnets in different AZs for EKS worker nodes
- ✅ Internet Gateway for public subnet access
- ✅ 2 NAT Gateways (one per public subnet) for private subnet egress
- ✅ Proper route table configuration
- ✅ Required security groups with appropriate rules
- ✅ Descriptive naming convention (envoy-poc-*)
- ✅ Pulumi config for all configurable values
- ✅ KMS encryption for state
- ✅ S3 backend for state storagehon S3 Bucket Pulumi Template

 A minimal Pulumi template for provisioning a single AWS S3 bucket using Python.

 ## Overview

 This template provisions an S3 bucket (`pulumi_aws.s3.BucketV2`) in your AWS account and exports its ID as an output. It’s an ideal starting point when:
  - You want to learn Pulumi with AWS in Python.
  - You need a barebones S3 bucket deployment to build upon.
  - You prefer a minimal template without extra dependencies.

 ## Prerequisites

 - An AWS account with permissions to create S3 buckets.
 - AWS credentials configured in your environment (for example via AWS CLI or environment variables).
 - Python 3.6 or later installed.
 - Pulumi CLI already installed and logged in.

 ## Getting Started

 1. Generate a new project from this template:
    ```bash
    pulumi new aws-python
    ```
 2. Follow the prompts to set your project name and AWS region (default: `us-east-1`).
 3. Change into your project directory:
    ```bash
    cd <project-name>
    ```
 4. Preview the planned changes:
    ```bash
    pulumi preview
    ```
 5. Deploy the stack:
    ```bash
    pulumi up
    ```
 6. Tear down when finished:
    ```bash
    pulumi destroy
    ```

 ## Project Layout

 After running `pulumi new`, your directory will look like:
 ```
 ├── __main__.py         # Entry point of the Pulumi program
 ├── Pulumi.yaml         # Project metadata and template configuration
 ├── requirements.txt    # Python dependencies
 └── Pulumi.<stack>.yaml # Stack-specific configuration (e.g., Pulumi.dev.yaml)
 ```

 ## Configuration

 This template defines the following config value:

 - `aws:region` (string)
   The AWS region to deploy resources into.
   Default: `us-east-1`

 View or update configuration with:
 ```bash
 pulumi config get aws:region
 pulumi config set aws:region us-west-2
 ```

 ## Outputs

 Once deployed, the stack exports:

 - `bucket_name` — the ID of the created S3 bucket.

 Retrieve outputs with:
 ```bash
 pulumi stack output bucket_name
 ```

 ## Next Steps

 - Customize `__main__.py` to add or configure additional resources.
 - Explore the Pulumi AWS SDK: https://www.pulumi.com/registry/packages/aws/
 - Break your infrastructure into modules for better organization.
 - Integrate into CI/CD pipelines for automated deployments.

 ## Help and Community

 If you have questions or need assistance:
 - Pulumi Documentation: https://www.pulumi.com/docs/
 - Community Slack: https://slack.pulumi.com/
 - GitHub Issues: https://github.com/pulumi/pulumi/issues

 Contributions and feedback are always welcome!