"""
AWS EKS Cluster Infrastructure for Envoy Proxy POC

This module creates the EKS cluster and managed node groups
according to the requirements in section 3.
"""

import pulumi
import pulumi_aws as aws
import pulumi_eks as eks
from typing import Dict, List, Any
from networking import get_provider_opts

# Import the AWS provider from networking module
from networking import aws_provider


class EKSConfig:
    """Configuration class for EKS cluster parameters"""
    CLUSTER_NAME = "envoy-poc"
    # Kubernetes version as specified in requirements.txt section 3
    KUBERNETES_VERSION = "1.33"
    NODE_INSTANCE_TYPE = "t3.medium"
    NODE_DESIRED_CAPACITY = 2
    NODE_MIN_CAPACITY = 2
    NODE_MAX_CAPACITY = 4
    NODE_AMI_TYPE = "AL2_x86_64"


def create_eks_service_role() -> aws.iam.Role:
    """Create IAM service role for EKS cluster"""
    
    # EKS service role trust policy
    eks_trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "eks.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    eks_service_role = aws.iam.Role(
        "envoy_poc_eks_service_role",
        name="envoy-poc-eks-service-role",
        assume_role_policy=pulumi.Output.json_dumps(eks_trust_policy),
        tags={
            "Name": "envoy-poc-eks-service-role",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        },
        opts=get_provider_opts()
    )
    
    # Attach required AWS managed policies
    aws.iam.RolePolicyAttachment(
        "envoy_poc_eks_cluster_policy",
        role=eks_service_role.name,
        policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
        opts=get_provider_opts()
    )
    
    return eks_service_role


def create_node_group_role() -> aws.iam.Role:
    """Create IAM role for EKS node group"""
    
    # Node group trust policy
    node_trust_policy = {
        "Version": "2012-10-17",
        "Statement": [
            {
                "Effect": "Allow",
                "Principal": {
                    "Service": "ec2.amazonaws.com"
                },
                "Action": "sts:AssumeRole"
            }
        ]
    }
    
    node_group_role = aws.iam.Role(
        "envoy_poc_node_group_role",
        name="envoy-poc-node-group-role",
        assume_role_policy=pulumi.Output.json_dumps(node_trust_policy),
        tags={
            "Name": "envoy-poc-node-group-role",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        },
        opts=get_provider_opts()
    )
    
    # Attach required AWS managed policies for worker nodes
    policies = [
        "arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
        "arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
        "arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly"
    ]
    
    for i, policy_arn in enumerate(policies):
        aws.iam.RolePolicyAttachment(
            f"envoy_poc_node_group_policy_{i}",
            role=node_group_role.name,
            policy_arn=policy_arn,
            opts=get_provider_opts()
        )
    
    return node_group_role


def create_cloudwatch_log_group() -> aws.cloudwatch.LogGroup:
    """Create CloudWatch log group for EKS control plane logs"""
    
    log_group = aws.cloudwatch.LogGroup(
        "envoy_poc_eks_log_group",
        name=f"/aws/eks/{EKSConfig.CLUSTER_NAME}/cluster",
        retention_in_days=7,  # 7 days retention for POC
        tags={
            "Name": f"envoy-poc-eks-logs",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        },
        opts=get_provider_opts()
    )
    
    return log_group


def create_eks_cluster(
    vpc_id: pulumi.Output[str],
    private_subnet_ids: List[pulumi.Output[str]],
    public_subnet_ids: List[pulumi.Output[str]],
    eks_cluster_sg_id: pulumi.Output[str]
) -> aws.eks.Cluster:
    """Create the EKS cluster"""
    
    # Create service role and log group
    eks_service_role = create_eks_service_role()
    log_group = create_cloudwatch_log_group()
    
    # Combine private and public subnet IDs for cluster
    all_subnet_ids = private_subnet_ids + public_subnet_ids
    
    eks_cluster = aws.eks.Cluster(
        "envoy_poc_eks_cluster",
        name=EKSConfig.CLUSTER_NAME,
        version=EKSConfig.KUBERNETES_VERSION,
        role_arn=eks_service_role.arn,
        
        # VPC configuration
        vpc_config=aws.eks.ClusterVpcConfigArgs(
            subnet_ids=all_subnet_ids,
            security_group_ids=[eks_cluster_sg_id],
            endpoint_private_access=True,
            endpoint_public_access=True,
            # Restrict public access to specific CIDR blocks if needed
            public_access_cidrs=["0.0.0.0/0"]
        ),
        
        # Enable control plane logging
        enabled_cluster_log_types=[
            "api",
            "audit", 
            "authenticator",
            "scheduler"
        ],
        
        # Encryption config (optional but recommended)
        encryption_config=aws.eks.ClusterEncryptionConfigArgs(
            provider=aws.eks.ClusterEncryptionConfigProviderArgs(
                key_arn=aws.kms.get_alias(
                    name="alias/pulumi-envoy-proxy-iac",
                    opts=pulumi.InvokeOptions(provider=aws_provider)
                ).target_key_arn
            ),
            resources=["secrets"]
        ),
        
        # Depends on log group to ensure it exists before cluster creation
        opts=get_provider_opts().merge(pulumi.ResourceOptions(
            depends_on=[log_group]
        )),
        
        tags={
            "Name": EKSConfig.CLUSTER_NAME,
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        }
    )
    
    return eks_cluster


def create_node_group(
    cluster: aws.eks.Cluster,
    private_subnet_ids: List[pulumi.Output[str]],
    worker_node_sg_id: pulumi.Output[str]
) -> aws.eks.NodeGroup:
    """Create the managed node group for the EKS cluster"""
    
    # Create node group role
    node_group_role = create_node_group_role()
    
    node_group = aws.eks.NodeGroup(
        "envoy_poc_node_group",
        cluster_name=cluster.name,
        node_group_name="envoy-poc-workers",
        node_role_arn=node_group_role.arn,
        subnet_ids=private_subnet_ids,  # Worker nodes in private subnets
        
        # Instance configuration
        instance_types=[EKSConfig.NODE_INSTANCE_TYPE],
        ami_type=EKSConfig.NODE_AMI_TYPE,
        capacity_type="ON_DEMAND",
        disk_size=20,  # 20GB disk per node
        
        # Scaling configuration
        scaling_config=aws.eks.NodeGroupScalingConfigArgs(
            desired_size=EKSConfig.NODE_DESIRED_CAPACITY,
            min_size=EKSConfig.NODE_MIN_CAPACITY,
            max_size=EKSConfig.NODE_MAX_CAPACITY
        ),
        
        # Update configuration
        update_config=aws.eks.NodeGroupUpdateConfigArgs(
            max_unavailable_percentage=25
        ),
        
        # Remote access configuration (optional - for debugging)
        # Uncomment if you need SSH access to worker nodes
        # remote_access=aws.eks.NodeGroupRemoteAccessArgs(
        #     ec2_ssh_key="your-key-pair-name"
        # ),
        
        # Ensure nodes are deployed after cluster is ready
        opts=get_provider_opts().merge(pulumi.ResourceOptions(
            depends_on=[cluster]
        )),
        
        tags={
            "Name": "envoy-poc-worker-nodes",
            "Project": "envoy-proxy-poc",
            "Environment": "poc",
            f"kubernetes.io/cluster/{EKSConfig.CLUSTER_NAME}": "owned"
        }
    )
    
    return node_group


def create_addon_vpc_cni(cluster: aws.eks.Cluster) -> aws.eks.Addon:
    """Create VPC CNI addon for the cluster"""
    
    vpc_cni_addon = aws.eks.Addon(
        "envoy_poc_vpc_cni_addon",
        cluster_name=cluster.name,
        addon_name="vpc-cni",
        addon_version="v1.18.1-eksbuild.1",  # Use appropriate version
        resolve_conflicts_on_create="OVERWRITE",
        tags={
            "Name": "envoy-poc-vpc-cni",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        },
        opts=get_provider_opts().merge(pulumi.ResourceOptions(
            depends_on=[cluster]
        ))
    )
    
    return vpc_cni_addon


def create_addon_coredns(cluster: aws.eks.Cluster, node_group: aws.eks.NodeGroup) -> aws.eks.Addon:
    """Create CoreDNS addon for the cluster"""
    
    coredns_addon = aws.eks.Addon(
        "envoy_poc_coredns_addon",
        cluster_name=cluster.name,
        addon_name="coredns",
        addon_version="v1.11.1-eksbuild.9",  # Use appropriate version
        resolve_conflicts_on_create="OVERWRITE",
        tags={
            "Name": "envoy-poc-coredns",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        },
        opts=get_provider_opts().merge(pulumi.ResourceOptions(
            depends_on=[cluster, node_group]
        ))
    )
    
    return coredns_addon


def create_addon_kube_proxy(cluster: aws.eks.Cluster) -> aws.eks.Addon:
    """Create kube-proxy addon for the cluster"""
    
    kube_proxy_addon = aws.eks.Addon(
        "envoy_poc_kube_proxy_addon",
        cluster_name=cluster.name,
        addon_name="kube-proxy",
        addon_version="v1.33.0-eksbuild.1",  # Version aligned with K8s 1.33
        resolve_conflicts_on_create="OVERWRITE",
        tags={
            "Name": "envoy-poc-kube-proxy",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        },
        opts=get_provider_opts().merge(pulumi.ResourceOptions(
            depends_on=[cluster]
        ))
    )
    
    return kube_proxy_addon


def create_eks_infrastructure(networking_infrastructure: Dict[str, Any]) -> Dict[str, Any]:
    """Main function to create EKS cluster and all related components"""
    
    # Extract networking components
    vpc = networking_infrastructure["vpc"]
    private_subnets = networking_infrastructure["private_subnets"]
    public_subnets = networking_infrastructure["public_subnets"]
    security_groups = networking_infrastructure["security_groups"]
    
    # Get subnet and security group IDs
    private_subnet_ids = [subnet.id for subnet in private_subnets]
    public_subnet_ids = [subnet.id for subnet in public_subnets]
    eks_cluster_sg_id = security_groups["eks_cluster"].id
    worker_node_sg_id = security_groups["worker_node"].id
    
    # Create EKS cluster
    eks_cluster = create_eks_cluster(
        vpc.id,
        private_subnet_ids,
        public_subnet_ids,
        eks_cluster_sg_id
    )
    
    # Create node group
    node_group = create_node_group(
        eks_cluster,
        private_subnet_ids,
        worker_node_sg_id
    )
    
    # Create essential addons
    vpc_cni_addon = create_addon_vpc_cni(eks_cluster)
    coredns_addon = create_addon_coredns(eks_cluster, node_group)
    kube_proxy_addon = create_addon_kube_proxy(eks_cluster)
    
    # Export important values
    pulumi.export("eks_cluster_name", eks_cluster.name)
    pulumi.export("eks_cluster_endpoint", eks_cluster.endpoint)
    pulumi.export("eks_cluster_version", eks_cluster.version)
    pulumi.export("eks_cluster_arn", eks_cluster.arn)
    pulumi.export("eks_cluster_status", eks_cluster.status)
    pulumi.export("eks_node_group_status", node_group.status)
    pulumi.export("eks_node_group_arn", node_group.arn)
    
    # Export kubeconfig command
    pulumi.export("kubeconfig_command", 
        f"aws eks update-kubeconfig --name {EKSConfig.CLUSTER_NAME} --region us-west-2 --profile avive-cfndev-k8s"
    )
    
    return {
        "cluster": eks_cluster,
        "node_group": node_group,
        "addons": {
            "vpc_cni": vpc_cni_addon,
            "coredns": coredns_addon,
            "kube_proxy": kube_proxy_addon
        }
    }


if __name__ == "__main__":
    # This module is designed to be imported and used by __main__.py
    pass
