# Envoy Proxy POC - AWS EKS Infrastructure

This project implements a Proof of Concept (POC) for deploying an AWS EKS cluster with Envoy proxy as a reverse proxy for WebSocket applications, built using Pulumi with Python.

## Project Status

### ✅ Completed Components

1. **AWS Networking Infrastructure (Section 2)**
   - VPC with CIDR 172.245.0.0/16
   - 2 Public subnets and 2 Private subnets across different AZs
   - Internet Gateway and NAT Gateways
   - Route Tables configuration
   - Security Groups for EKS, ALB, and Envoy services

### 🚧 Pending Components

2. **EKS Cluster (Section 3)** - Not yet implemented
3. **Container Registries (Section 4)** - Not yet implemented  
4. **Server Application (Section 5)** - Not yet implemented
5. **Envoy Proxy Setup (Section 6)** - Not yet implemented
6. **Client Application (Section 7)** - Not yet implemented
7. **Post-Deployment Verification (Section 8)** - Not yet implemented

## Quick Start - Networking Infrastructure

1. **Prerequisites**:
   - Pulumi CLI installed
   - AWS CLI configured with profile `avive-cfndev-k8s`
   - Python 3.8+
   - S3 bucket `cfndev-envoy-proxy-poc-pulumi-state` must exist
   - KMS key with alias `pulumi-envoy-proxy-iac` for secrets encryption

2. **Deploy the networking infrastructure**:
   ```bash
   # Create KMS key if it doesn't exist
   ./create-kms-key.sh
   
   # Run the setup script
   ./setup.sh
   
   # Activate virtual environment
   source venv/bin/activate
   
   # Deploy the infrastructure
   pulumi up
   
   # Validate the deployment
   ./validate-networking.sh
   ```

## Configuration

This project uses centralized configuration to avoid hardcoded values. All configuration is managed in `config.sh`:

- **AWS Profile**: `avive-cfndev-k8s` (AWS SSO profile)
- **AWS Region**: `us-west-2`
- **KMS Key**: `alias/pulumi-envoy-proxy-iac`
- **Pulumi Stack**: `cfndev`

To customize configuration values, edit `config.sh`. All scripts will automatically use the updated values.

For detailed configuration documentation, see [CONFIG.md](CONFIG.md).

## Architecture Overview

The complete system will include:

- **AWS EKS Cluster**: Kubernetes cluster named 'envoy-poc'
- **Envoy Proxy**: Reverse proxy with WebSocket connection management
- **WebSocket Server**: Python application handling WebSocket connections
- **Client Application**: Test client for generating WebSocket traffic
- **AWS ALB**: Application Load Balancer for external access

## Project Structure

```
├── __main__.py                 # Main Pulumi program
├── networking.py               # AWS networking infrastructure
├── Pulumi.yaml                # Pulumi project configuration
├── Pulumi.cfndev.yaml         # Stack configuration
├── requirements-pulumi.txt     # Python dependencies
├── requirements.txt           # Project requirements document
├── setup.sh                   # Setup and initialization script
├── create-kms-key.sh          # KMS key creation script
├── validate-networking.sh     # Networking validation script
├── README.md                  # This file
└── README-networking.md       # Detailed networking documentation
```

## Documentation

- [`requirements.txt`](requirements.txt) - Complete project requirements
- [`README-networking.md`](README-networking.md) - Detailed networking infrastructure documentation

## Configuration

- **AWS Profile**: `avive-cfndev-k8s`
- **AWS Region**: `us-west-2` (configurable in `Pulumi.cfndev.yaml`)
- **Pulumi Backend**: S3 (`cfndev-envoy-proxy-poc-pulumi-state`)
- **Secrets Encryption**: AWS KMS (`alias/pulumi-envoy-proxy-iac`)
- **VPC CIDR**: `172.245.0.0/16`

## Next Steps

The next phase will implement:
1. EKS cluster deployment with managed node groups
2. ECR repositories for container images
3. WebSocket server and client applications
4. Envoy proxy configuration and deployment

---

For detailed implementation requirements, see [`requirements.txt`](requirements.txt).