# Envoy Proxy POC - AWS Networking Infrastructure

This directory contains the Pulumi infrastructure code for creating the AWS networking components required for the Envoy Proxy POC, including VPC, subnets, security groups, and routing configuration.

## Architecture Overview

The networking infrastructure creates:

### VPC Configuration
- **VPC Name**: `envoy-vpc`
- **CIDR Block**: `172.245.0.0/16`
- **DNS Hostnames**: Enabled
- **DNS Support**: Enabled

### Subnets
- **Public Subnets (2)**: 
  - `172.245.1.0/24` (AZ-1)
  - `172.245.2.0/24` (AZ-2)
  - Used for AWS ALB and NAT Gateways
- **Private Subnets (2)**:
  - `172.245.10.0/24` (AZ-1) 
  - `172.245.20.0/24` (AZ-2)
  - Used for EKS worker nodes and internal services

### Internet Connectivity
- **Internet Gateway**: Provides internet access for public subnets
- **NAT Gateways (2)**: One in each public subnet for private subnet egress
- **Elastic IPs (2)**: Associated with NAT Gateways

### Route Tables
- **Public Route Table**: Routes internet traffic (0.0.0.0/0) to Internet Gateway
- **Private Route Tables (2)**: One per AZ, routes internet traffic to respective NAT Gateway

### Security Groups
1. **EKS Cluster Security Group**: Controls communication between EKS control plane and worker nodes
2. **Worker Node Security Group**: Allows ingress from EKS cluster and egress to AWS services
3. **ALB Security Group**: Allows HTTP (port 80) and HTTPS (port 443) from internet
4. **Envoy Service Security Group**: Allows ingress from ALB and metrics access on port 9901

## Prerequisites

1. **Pulumi CLI**: Install from [pulumi.com](https://www.pulumi.com/docs/get-started/install/)
2. **AWS CLI**: Configured with profile `avive-cfndev-k8s`
3. **Python 3.8+**: Required for Pulumi Python runtime
4. **S3 Backend**: Bucket `cfndev-envoy-proxy-poc-pulumi-state` must exist
5. **KMS Key**: AWS KMS key with alias `pulumi-envoy-proxy-iac` for secrets encryption

## Quick Start

1. **Create KMS key (if it doesn't exist)**:
   ```bash
   ./create-kms-key.sh
   ```

2. **Run the setup script**:
   ```bash
   ./setup.sh
   ```

2. **Activate the virtual environment**:
   ```bash
   source venv/bin/activate
   ```

3. **Preview the infrastructure**:
   ```bash
   pulumi preview
   ```

4. **Deploy the infrastructure**:
   ```bash
   pulumi up
   ```

## Configuration

The infrastructure uses the following configuration:

- **AWS Profile**: `avive-cfndev-k8s` (configured via AWS SSO)
- **AWS Region**: `us-west-2` (configurable in `Pulumi.cfndev.yaml`)
- **Pulumi Backend**: S3 bucket `cfndev-envoy-proxy-poc-pulumi-state`
- **State Prefix**: `envoy-poc/`
- **Secrets Encryption**: AWS KMS key `alias/pulumi-envoy-proxy-iac`

## Outputs

After deployment, the following outputs are available:

```bash
pulumi stack output
```

Key outputs include:
- `vpc_id`: VPC identifier
- `public_subnet_ids`: List of public subnet IDs
- `private_subnet_ids`: List of private subnet IDs
- `*_security_group_id`: Security group identifiers
- `availability_zones`: AZs used for deployment

## File Structure

```
├── __main__.py              # Main Pulumi program entry point
├── networking.py            # Networking infrastructure module
├── Pulumi.yaml             # Pulumi project configuration
├── Pulumi.cfndev.yaml      # Stack-specific configuration
├── requirements-pulumi.txt  # Python dependencies
├── setup.sh               # Setup and initialization script
├── create-kms-key.sh      # KMS key creation script
├── validate-networking.sh # Infrastructure validation script
└── README-networking.md   # This file
```

## Security Considerations

- Private subnets have no direct internet access (only through NAT Gateways)
- Security groups follow principle of least privilege
- EKS cluster tags are applied for proper resource discovery
- All resources are tagged for identification and cost allocation
- **Secrets Encryption**: All Pulumi secrets are encrypted using AWS KMS (no passwords required)
- **Least Privilege**: KMS key access is limited to authorized AWS profiles only

## Cost Optimization

- NAT Gateways are the primary cost drivers (~$45/month each)
- Elastic IPs are allocated only when associated with NAT Gateways
- Consider using NAT Instances for development environments to reduce costs

## Troubleshooting

### Common Issues

1. **AWS Profile Issues**:
   ```bash
   aws sts get-caller-identity --profile avive-cfndev-k8s
   ```

2. **S3 Backend Access**:
   ```bash
   aws s3 ls s3://cfndev-envoy-proxy-poc-pulumi-state --profile avive-cfndev-k8s
   ```

3. **Pulumi State Issues**:
   ```bash
   pulumi refresh
   ```

### Cleanup

To destroy the infrastructure:

```bash
pulumi destroy
```

**Note**: This will delete all AWS resources created by this stack. Ensure you have backups of any important data.

## Next Steps

After the networking infrastructure is deployed:

1. Deploy the EKS cluster (Section 3 of requirements)
2. Set up ECR repositories (Section 4 of requirements)
3. Deploy the server and client applications (Sections 5 & 7)
4. Configure Envoy proxy (Section 6)

## Support

For issues or questions, refer to:
- [Pulumi AWS Provider Documentation](https://www.pulumi.com/registry/packages/aws/)
- [AWS VPC Documentation](https://docs.aws.amazon.com/vpc/)
- [EKS Networking Documentation](https://docs.aws.amazon.com/eks/latest/userguide/network_reqs.html)
