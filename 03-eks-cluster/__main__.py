"""
AWS EKS Cluster Infrastructure for Envoy Proxy POC
Requirement Section 3: EKS Cluster Details

This module creates:
- EKS Cluster with specified configuration
- EKS Managed Node Group
- Required IAM roles and policies
- Control plane logging configuration
"""

import pulumi
import pulumi_aws as aws
from pulumi_aws import iam

# Get current AWS account and region information
current_account = aws.get_caller_identity()
current_region = aws.get_region()

# Get configuration values
config = pulumi.Config()
cluster_name = config.require("cluster_name")
kubernetes_version = config.require("kubernetes_version")
project_name = config.require("project_name")
node_instance_type = config.require("node_instance_type")
node_desired_capacity = config.require_int("node_desired_capacity")
node_min_capacity = config.require_int("node_min_capacity")
node_max_capacity = config.require_int("node_max_capacity")
node_ami_type = config.require("node_ami_type")
networking_stack_name = config.require("networking_stack_name")
kms_key_alias = config.require("kms_key_alias")

# Get current stack name to use for referencing other stacks
current_stack = pulumi.get_stack()

# Reference the networking stack to get VPC and subnet information
networking_stack = pulumi.StackReference(f"{networking_stack_name}/{current_stack}")

# Get networking resources from the referenced stack
vpc_id = networking_stack.get_output("vpc_id")
private_subnet_ids = networking_stack.get_output("private_subnet_ids")
public_subnet_ids = networking_stack.get_output("public_subnet_ids")
eks_cluster_sg_id = networking_stack.get_output("eks_cluster_sg_id")
worker_node_sg_id = networking_stack.get_output("worker_node_sg_id")

# Create EKS Cluster Service Role
eks_cluster_service_role = iam.Role(
    "envoy-poc-eks-cluster-service-role",
    assume_role_policy=pulumi.Output.json_dumps({
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
    }),
    tags={
        "Name": f"{project_name}-eks-cluster-service-role",
        "Project": project_name
    }
)

# Attach required policies to the EKS cluster service role
eks_cluster_policy_attachment = iam.RolePolicyAttachment(
    "envoy-poc-eks-cluster-policy-attachment",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSClusterPolicy",
    role=eks_cluster_service_role.name
)

# Create EKS Node Group Service Role
eks_node_group_service_role = iam.Role(
    "envoy-poc-eks-node-group-service-role",
    assume_role_policy=pulumi.Output.json_dumps({
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
    }),
    tags={
        "Name": f"{project_name}-eks-node-group-service-role",
        "Project": project_name
    }
)

# Attach required policies to the EKS node group service role
worker_node_policy_attachment = iam.RolePolicyAttachment(
    "envoy-poc-worker-node-policy-attachment",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKSWorkerNodePolicy",
    role=eks_node_group_service_role.name
)

cni_policy_attachment = iam.RolePolicyAttachment(
    "envoy-poc-cni-policy-attachment",
    policy_arn="arn:aws:iam::aws:policy/AmazonEKS_CNI_Policy",
    role=eks_node_group_service_role.name
)

registry_read_only_attachment = iam.RolePolicyAttachment(
    "envoy-poc-registry-read-only-attachment",
    policy_arn="arn:aws:iam::aws:policy/AmazonEC2ContainerRegistryReadOnly",
    role=eks_node_group_service_role.name
)

# Create CloudWatch Log Group for EKS control plane logs
eks_log_group = aws.cloudwatch.LogGroup(
    "envoy-poc-eks-cluster-logs",
    name=f"/aws/eks/{cluster_name}/cluster",
    retention_in_days=7,
    tags={
        "Name": f"{project_name}-eks-cluster-logs",
        "Project": project_name
    }
)

# Create EKS Cluster
envoy_poc_eks_cluster = aws.eks.Cluster(
    "envoy-poc-eks-cluster",
    name=cluster_name,
    version=kubernetes_version,
    role_arn=eks_cluster_service_role.arn,
    vpc_config=aws.eks.ClusterVpcConfigArgs(
        subnet_ids=pulumi.Output.all(private_subnet_ids, public_subnet_ids).apply(
            lambda subnets: subnets[0] + subnets[1]
        ),
        security_group_ids=[eks_cluster_sg_id],
        endpoint_config=aws.eks.ClusterVpcConfigEndpointConfigArgs(
            private_access=True,
            public_access=True
        )
    ),
    enabled_cluster_log_types=[
        "api",
        "audit", 
        "authenticator",
        "scheduler"
    ],
    encryption_config=aws.eks.ClusterEncryptionConfigArgs(
        provider=aws.eks.ClusterEncryptionConfigProviderArgs(
            key_arn=pulumi.Output.all(current_account.account_id, current_region.name, kms_key_alias).apply(
                lambda args: f"arn:aws:kms:{args[1]}:{args[0]}:{args[2]}"
            )
        ),
        resources=["secrets"]
    ),
    tags={
        "Name": f"{project_name}-eks-cluster",
        "Project": project_name,
        "Environment": "poc"
    },
    opts=pulumi.ResourceOptions(
        depends_on=[
            eks_cluster_policy_attachment,
            eks_log_group
        ]
    )
)

# Create EKS Managed Node Group
envoy_poc_node_group = aws.eks.NodeGroup(
    "envoy-poc-eks-node-group",
    cluster_name=envoy_poc_eks_cluster.name,
    node_group_name=f"{cluster_name}-node-group",
    node_role_arn=eks_node_group_service_role.arn,
    subnet_ids=private_subnet_ids,
    instance_types=[node_instance_type],
    ami_type=node_ami_type,
    capacity_type="ON_DEMAND",
    disk_size=20,
    scaling_config=aws.eks.NodeGroupScalingConfigArgs(
        desired_size=node_desired_capacity,
        min_size=node_min_capacity,
        max_size=node_max_capacity
    ),
    update_config=aws.eks.NodeGroupUpdateConfigArgs(
        max_unavailable_percentage=25
    ),
    remote_access=aws.eks.NodeGroupRemoteAccessArgs(
        ec2_ssh_key="",  # No SSH key for this POC
        source_security_group_ids=[worker_node_sg_id]
    ),
    tags={
        "Name": f"{project_name}-eks-node-group",
        "Project": project_name,
        "Environment": "poc"
    },
    opts=pulumi.ResourceOptions(
        depends_on=[
            worker_node_policy_attachment,
            cni_policy_attachment,
            registry_read_only_attachment
        ]
    )
)

# Export important resource information for use by other stacks
pulumi.export("cluster_name", envoy_poc_eks_cluster.name)
pulumi.export("cluster_arn", envoy_poc_eks_cluster.arn)
pulumi.export("cluster_endpoint", envoy_poc_eks_cluster.endpoint)
pulumi.export("cluster_version", envoy_poc_eks_cluster.version)
pulumi.export("cluster_certificate_authority_data", envoy_poc_eks_cluster.certificate_authority.data)
pulumi.export("cluster_security_group_id", envoy_poc_eks_cluster.vpc_config.cluster_security_group_id)
pulumi.export("node_group_arn", envoy_poc_node_group.arn)
pulumi.export("node_group_status", envoy_poc_node_group.status)
pulumi.export("cluster_oidc_issuer_url", envoy_poc_eks_cluster.identities[0].oidcs[0].issuer)

# Export kubeconfig information
pulumi.export("kubeconfig_update_command", 
             pulumi.Output.all(cluster_name, current_region.name).apply(
                 lambda args: f"aws eks update-kubeconfig --name {args[0]} --region {args[1]} --profile avive-cfndev-k8s"
             ))
