# EKS Cluster Infrastructure Documentation

This document provides detailed information about the EKS cluster implementation for the Envoy Proxy POC (Section 3 of requirements).

## Overview

The EKS cluster implementation creates a production-ready Kubernetes cluster named `envoy-poc` with managed worker nodes, essential addons, and proper security configurations.

## Architecture

### EKS Cluster Configuration

- **Cluster Name**: `envoy-poc`
- **Kubernetes Version**: `1.33` (as specified in requirements)
- **API Endpoints**: Both public and private access enabled
- **Control Plane Logging**: Enabled for `api`, `audit`, `authenticator`, and `scheduler`
- **Encryption**: Secrets encrypted at rest using KMS key `alias/pulumi-envoy-proxy-iac`

### Node Group Configuration

- **Node Group Name**: `envoy-poc-workers`
- **Instance Type**: `t3.medium`
- **AMI Type**: `AL2_x86_64` (Amazon Linux 2)
- **Capacity**: 
  - Desired: 2 nodes
  - Minimum: 2 nodes
  - Maximum: 4 nodes
- **Disk Size**: 20GB per node
- **Capacity Type**: On-Demand instances
- **Subnets**: Deployed in private subnets for security

### Essential Addons

The cluster includes the following AWS managed addons:

1. **VPC CNI** (`vpc-cni`): Provides native VPC networking for pods
2. **CoreDNS** (`coredns`): DNS server for service discovery within the cluster
3. **kube-proxy** (`kube-proxy`): Maintains network rules on nodes

## Security Configuration

### IAM Roles

1. **EKS Service Role** (`envoy-poc-eks-service-role`)
   - Allows EKS to manage the cluster control plane
   - Attached policies: `AmazonEKSClusterPolicy`

2. **Node Group Role** (`envoy-poc-node-group-role`)
   - Allows worker nodes to join the cluster and pull container images
   - Attached policies:
     - `AmazonEKSWorkerNodePolicy`
     - `AmazonEKS_CNI_Policy`
     - `AmazonEC2ContainerRegistryReadOnly`

### Security Groups

The cluster leverages security groups created by the networking module:

- **EKS Cluster Security Group**: Controls traffic to/from the control plane
- **Worker Node Security Group**: Controls traffic to/from worker nodes
- **ALB Security Group**: For future ALB integration
- **Envoy Service Security Group**: For future Envoy proxy deployment

## Networking Integration

The EKS cluster is integrated with the VPC infrastructure:

- **VPC**: `envoy-vpc` (172.245.0.0/16)
- **Control Plane Subnets**: Both public and private subnets (for high availability)
- **Worker Node Subnets**: Private subnets only (for security)
- **Internet Access**: Through NAT Gateways in public subnets

## Monitoring and Logging

### CloudWatch Logs

Control plane logs are sent to CloudWatch log group: `/aws/eks/envoy-poc/cluster`

Enabled log types:
- **API Server logs**: All requests to the Kubernetes API server
- **Audit logs**: Audit events that passed through the API server
- **Authenticator logs**: Authentiation and authorization attempts
- **Scheduler logs**: Decisions made by the kube-scheduler

### Log Retention

- **Retention Period**: 7 days (appropriate for POC environment)
- **Cost Optimization**: Short retention period to minimize CloudWatch costs

## File Structure

```
├── eks_cluster.py              # EKS cluster infrastructure code
├── validate-eks.sh             # EKS cluster validation script
├── README-eks.md              # This documentation file
└── config.sh                 # Updated with CLUSTER_NAME variable
```

## Key Functions in eks_cluster.py

### Core Components

1. **`create_eks_service_role()`**: Creates IAM role for EKS cluster
2. **`create_node_group_role()`**: Creates IAM role for worker nodes
3. **`create_cloudwatch_log_group()`**: Sets up control plane logging
4. **`create_eks_cluster()`**: Creates the main EKS cluster
5. **`create_node_group()`**: Creates managed node group
6. **`create_addon_*()`**: Creates essential addons (VPC CNI, CoreDNS, kube-proxy)

### Main Function

**`create_eks_infrastructure(networking_infrastructure)`**: Orchestrates the creation of all EKS components

## Validation

Use the validation script to verify the cluster deployment:

```bash
./validate-eks.sh
```

The script performs the following checks:
1. EKS cluster status (should be ACTIVE)
2. Node group status (should be ACTIVE) 
3. Node group capacity configuration
4. kubectl connectivity
5. Worker node availability (minimum 2 nodes)
6. System pod health
7. Addon installation status

## Kubeconfig Access

After deployment, configure kubectl access:

```bash
aws eks update-kubeconfig --name envoy-poc --region us-west-2 --profile avive-cfndev-k8s
```

This command is also available in the Pulumi outputs as `kubeconfig_command`.

## Resource Tagging

All resources are tagged with:
- **Name**: Descriptive resource name
- **Project**: `envoy-proxy-poc`
- **Environment**: `poc`
- **kubernetes.io/cluster/envoy-poc**: `owned` or `shared` (for AWS Load Balancer Controller)

## Next Steps

After the EKS cluster is deployed and validated:

1. **Container Registries (Section 4)**: Create ECR repositories
2. **Application Deployment (Section 5)**: Build and deploy WebSocket server
3. **Envoy Proxy Setup (Section 6)**: Deploy Envoy as reverse proxy
4. **Client Application (Section 7)**: Deploy test client application
5. **Load Balancer**: Deploy AWS Load Balancer Controller for external access

## Troubleshooting

### Common Issues

1. **Cluster Creation Timeout**
   - Check subnet configurations and security groups
   - Verify IAM roles have correct permissions
   - Check CloudWatch logs for detailed error messages

2. **Node Group Not Joining**
   - Verify security group rules allow communication
   - Check that private subnets have NAT Gateway access
   - Ensure node group role has required policies

3. **kubectl Access Issues**
   - Run kubeconfig update command
   - Verify AWS CLI profile has EKS permissions
   - Check cluster endpoint accessibility

### Useful Commands

```bash
# Check cluster status
aws eks describe-cluster --name envoy-poc --profile avive-cfndev-k8s

# Check node group status  
aws eks describe-nodegroup --cluster-name envoy-poc --nodegroup-name envoy-poc-workers --profile avive-cfndev-k8s

# List cluster addons
aws eks list-addons --cluster-name envoy-poc --profile avive-cfndev-k8s

# View cluster nodes
kubectl get nodes -o wide

# Check system pods
kubectl get pods -n kube-system
```

## Cost Considerations

### Estimated Monthly Costs (us-west-2)

- **EKS Cluster**: ~$73/month (control plane)
- **EC2 Instances**: ~$60/month (2 x t3.medium)
- **EBS Storage**: ~$4/month (2 x 20GB volumes)
- **NAT Gateways**: ~$90/month (2 NAT GW + data transfer)
- **CloudWatch Logs**: ~$5/month (estimated log volume)

**Total Estimated**: ~$232/month

*Note: Costs may vary based on actual usage, data transfer, and AWS pricing changes.*

## Security Best Practices Implemented

1. **Network Isolation**: Worker nodes in private subnets
2. **Encryption**: Secrets encrypted at rest with KMS
3. **IAM**: Least privilege roles for cluster and nodes
4. **Logging**: Comprehensive control plane logging
5. **Updates**: Managed node groups for automated updates
6. **Security Groups**: Restricted traffic flows between components

This EKS cluster provides a solid foundation for deploying the Envoy proxy and WebSocket applications in subsequent sections.
