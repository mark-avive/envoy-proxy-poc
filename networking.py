"""
AWS Networking Infrastructure for Envoy Proxy POC

This module creates the VPC, subnets, security groups, and networking components
required for the EKS cluster and Envoy proxy setup.
"""

import pulumi
import pulumi_aws as aws
from typing import List, Dict, Any

# Create explicit AWS provider since default providers are disabled
config = pulumi.Config("aws")
aws_provider = aws.Provider("aws-provider",
    region=config.get("region"),
    profile=config.get("profile")
)

def get_provider_opts() -> pulumi.ResourceOptions:
    """Helper function to get resource options with the AWS provider"""
    return pulumi.ResourceOptions(provider=aws_provider)


class NetworkingConfig:
    """Configuration class for networking parameters"""
    VPC_CIDR = "172.245.0.0/16"
    VPC_NAME = "envoy-vpc"
    
    # Subnet CIDRs - ensuring proper distribution across AZs
    PUBLIC_SUBNET_CIDRS = ["172.245.1.0/24", "172.245.2.0/24"]
    PRIVATE_SUBNET_CIDRS = ["172.245.10.0/24", "172.245.20.0/24"]


def create_vpc() -> aws.ec2.Vpc:
    """Create the main VPC for the environment"""
    vpc = aws.ec2.Vpc(
        "envoy_poc_vpc",
        cidr_block=NetworkingConfig.VPC_CIDR,
        enable_dns_hostnames=True,
        enable_dns_support=True,
        tags={
            "Name": NetworkingConfig.VPC_NAME,
            "Project": "envoy-proxy-poc",
            "Environment": "poc",
            "kubernetes.io/cluster/envoy-poc": "shared"
        },
        opts=get_provider_opts()
    )
    
    pulumi.export("vpc_id", vpc.id)
    pulumi.export("vpc_cidr", vpc.cidr_block)
    
    return vpc


def get_availability_zones() -> List[str]:
    """Get available AZs in the current region"""
    azs = aws.get_availability_zones(state="available", opts=pulumi.InvokeOptions(provider=aws_provider))
    return azs.names[:2]  # Use first 2 AZs


def create_internet_gateway(vpc: aws.ec2.Vpc) -> aws.ec2.InternetGateway:
    """Create Internet Gateway for public subnet access"""
    igw = aws.ec2.InternetGateway(
        "envoy_poc_igw",
        vpc_id=vpc.id,
        tags={
            "Name": "envoy-poc-igw",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        }
    )
    
    pulumi.export("internet_gateway_id", igw.id)
    return igw


def create_public_subnets(vpc: aws.ec2.Vpc, availability_zones: List[str]) -> List[aws.ec2.Subnet]:
    """Create public subnets for ALB and NAT Gateways"""
    public_subnets = []
    
    for i, (cidr, az) in enumerate(zip(NetworkingConfig.PUBLIC_SUBNET_CIDRS, availability_zones)):
        subnet = aws.ec2.Subnet(
            f"envoy_poc_public_subnet_{i+1}",
            vpc_id=vpc.id,
            cidr_block=cidr,
            availability_zone=az,
            map_public_ip_on_launch=True,
            tags={
                "Name": f"envoy-poc-public-subnet-{i+1}",
                "Project": "envoy-proxy-poc",
                "Environment": "poc",
                "kubernetes.io/role/elb": "1",
                "kubernetes.io/cluster/envoy-poc": "shared"
            }
        )
        public_subnets.append(subnet)
    
    pulumi.export("public_subnet_ids", [subnet.id for subnet in public_subnets])
    return public_subnets


def create_private_subnets(vpc: aws.ec2.Vpc, availability_zones: List[str]) -> List[aws.ec2.Subnet]:
    """Create private subnets for EKS worker nodes and internal services"""
    private_subnets = []
    
    for i, (cidr, az) in enumerate(zip(NetworkingConfig.PRIVATE_SUBNET_CIDRS, availability_zones)):
        subnet = aws.ec2.Subnet(
            f"envoy_poc_private_subnet_{i+1}",
            vpc_id=vpc.id,
            cidr_block=cidr,
            availability_zone=az,
            tags={
                "Name": f"envoy-poc-private-subnet-{i+1}",
                "Project": "envoy-proxy-poc",
                "Environment": "poc",
                "kubernetes.io/role/internal-elb": "1",
                "kubernetes.io/cluster/envoy-poc": "shared"
            }
        )
        private_subnets.append(subnet)
    
    pulumi.export("private_subnet_ids", [subnet.id for subnet in private_subnets])
    return private_subnets


def create_nat_gateways(public_subnets: List[aws.ec2.Subnet]) -> List[aws.ec2.NatGateway]:
    """Create NAT Gateways in each public subnet for private subnet egress"""
    nat_gateways = []
    
    for i, subnet in enumerate(public_subnets):
        # Create Elastic IP for NAT Gateway
        eip = aws.ec2.Eip(
            f"envoy_poc_nat_eip_{i+1}",
            domain="vpc",
            tags={
                "Name": f"envoy-poc-nat-eip-{i+1}",
                "Project": "envoy-proxy-poc",
                "Environment": "poc"
            },
            opts=get_provider_opts()
        )
        
        # Create NAT Gateway
        nat_gw = aws.ec2.NatGateway(
            f"envoy_poc_nat_gateway_{i+1}",
            allocation_id=eip.id,
            subnet_id=subnet.id,
            tags={
                "Name": f"envoy-poc-nat-gateway-{i+1}",
                "Project": "envoy-proxy-poc",
                "Environment": "poc"
            }
        )
        
        nat_gateways.append(nat_gw)
    
    pulumi.export("nat_gateway_ids", [nat_gw.id for nat_gw in nat_gateways])
    return nat_gateways


def create_route_tables(
    vpc: aws.ec2.Vpc, 
    igw: aws.ec2.InternetGateway,
    public_subnets: List[aws.ec2.Subnet],
    private_subnets: List[aws.ec2.Subnet],
    nat_gateways: List[aws.ec2.NatGateway]
) -> Dict[str, List[aws.ec2.RouteTable]]:
    """Create and configure route tables for public and private subnets"""
    
    # Public Route Table
    public_rt = aws.ec2.RouteTable(
        "envoy_poc_public_rt",
        vpc_id=vpc.id,
        tags={
            "Name": "envoy-poc-public-rt",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        }
    )
    
    # Public route to Internet Gateway
    aws.ec2.Route(
        "envoy_poc_public_route",
        route_table_id=public_rt.id,
        destination_cidr_block="0.0.0.0/0",
        gateway_id=igw.id
    )
    
    # Associate public subnets with public route table
    for i, subnet in enumerate(public_subnets):
        aws.ec2.RouteTableAssociation(
            f"envoy_poc_public_rta_{i+1}",
            subnet_id=subnet.id,
            route_table_id=public_rt.id
        )
    
    # Private Route Tables (one per AZ for high availability)
    private_rts = []
    for i, (subnet, nat_gw) in enumerate(zip(private_subnets, nat_gateways)):
        private_rt = aws.ec2.RouteTable(
            f"envoy_poc_private_rt_{i+1}",
            vpc_id=vpc.id,
            tags={
                "Name": f"envoy-poc-private-rt-{i+1}",
                "Project": "envoy-proxy-poc",
                "Environment": "poc"
            }
        )
        
        # Private route to NAT Gateway
        aws.ec2.Route(
            f"envoy_poc_private_route_{i+1}",
            route_table_id=private_rt.id,
            destination_cidr_block="0.0.0.0/0",
            nat_gateway_id=nat_gw.id
        )
        
        # Associate private subnet with its route table
        aws.ec2.RouteTableAssociation(
            f"envoy_poc_private_rta_{i+1}",
            subnet_id=subnet.id,
            route_table_id=private_rt.id
        )
        
        private_rts.append(private_rt)
    
    route_tables = {
        "public": [public_rt],
        "private": private_rts
    }
    
    pulumi.export("public_route_table_id", public_rt.id)
    pulumi.export("private_route_table_ids", [rt.id for rt in private_rts])
    
    return route_tables


def create_security_groups(vpc: aws.ec2.Vpc) -> Dict[str, aws.ec2.SecurityGroup]:
    """Create security groups for EKS cluster components"""
    
    security_groups = {}
    
    # EKS Cluster Security Group
    eks_cluster_sg = aws.ec2.SecurityGroup(
        "envoy_poc_eks_cluster_sg",
        name="envoy-poc-eks-cluster-sg",
        vpc_id=vpc.id,
        description="Security group for EKS cluster control plane",
        tags={
            "Name": "envoy-poc-eks-cluster-sg",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        }
    )
    
    # EKS Worker Node Security Group
    worker_node_sg = aws.ec2.SecurityGroup(
        "envoy_poc_worker_node_sg",
        name="envoy-poc-worker-node-sg",
        vpc_id=vpc.id,
        description="Security group for EKS worker nodes",
        tags={
            "Name": "envoy-poc-worker-node-sg",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        }
    )
    
    # ALB Security Group
    alb_sg = aws.ec2.SecurityGroup(
        "envoy_poc_alb_sg",
        name="envoy-poc-alb-sg",
        vpc_id=vpc.id,
        description="Security group for Application Load Balancer",
        ingress=[
            aws.ec2.SecurityGroupIngressArgs(
                from_port=80,
                to_port=80,
                protocol="tcp",
                cidr_blocks=["0.0.0.0/0"],
                description="HTTP traffic from internet"
            ),
            aws.ec2.SecurityGroupIngressArgs(
                from_port=443,
                to_port=443,
                protocol="tcp",
                cidr_blocks=["0.0.0.0/0"],
                description="HTTPS traffic from internet"
            )
        ],
        egress=[
            aws.ec2.SecurityGroupEgressArgs(
                from_port=0,
                to_port=0,
                protocol="-1",
                cidr_blocks=["0.0.0.0/0"],
                description="All outbound traffic"
            )
        ],
        tags={
            "Name": "envoy-poc-alb-sg",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        }
    )
    
    # Envoy Service Security Group
    envoy_service_sg = aws.ec2.SecurityGroup(
        "envoy_poc_envoy_service_sg",
        name="envoy-poc-envoy-service-sg",
        vpc_id=vpc.id,
        description="Security group for Envoy proxy service",
        tags={
            "Name": "envoy-poc-envoy-service-sg",
            "Project": "envoy-proxy-poc",
            "Environment": "poc"
        }
    )
    
    # Security Group Rules
    
    # Worker nodes can communicate with cluster API Server
    aws.ec2.SecurityGroupRule(
        "worker_to_cluster_api",
        type="egress",
        from_port=443,
        to_port=443,
        protocol="tcp",
        source_security_group_id=eks_cluster_sg.id,
        security_group_id=worker_node_sg.id,
        description="Worker node to cluster API server"
    )
    
    # Cluster API server can communicate with worker nodes
    aws.ec2.SecurityGroupRule(
        "cluster_to_worker_kubelet",
        type="egress",
        from_port=10250,
        to_port=10250,
        protocol="tcp",
        source_security_group_id=worker_node_sg.id,
        security_group_id=eks_cluster_sg.id,
        description="Cluster API to worker kubelet"
    )
    
    # Worker nodes can communicate with each other
    aws.ec2.SecurityGroupRule(
        "worker_to_worker_all",
        type="ingress",
        from_port=0,
        to_port=65535,
        protocol="tcp",
        source_security_group_id=worker_node_sg.id,
        security_group_id=worker_node_sg.id,
        description="Worker node to worker node communication"
    )
    
    # Worker nodes can access internet for pulling images, etc.
    aws.ec2.SecurityGroupRule(
        "worker_egress_internet",
        type="egress",
        from_port=0,
        to_port=0,
        protocol="-1",
        cidr_blocks=["0.0.0.0/0"],
        security_group_id=worker_node_sg.id,
        description="Worker node internet access"
    )
    
    # ALB can communicate with Envoy service
    aws.ec2.SecurityGroupRule(
        "alb_to_envoy",
        type="egress",
        from_port=80,
        to_port=80,
        protocol="tcp",
        source_security_group_id=envoy_service_sg.id,
        security_group_id=alb_sg.id,
        description="ALB to Envoy service"
    )
    
    # Envoy service can receive traffic from ALB
    aws.ec2.SecurityGroupRule(
        "envoy_from_alb",
        type="ingress",
        from_port=80,
        to_port=80,
        protocol="tcp",
        source_security_group_id=alb_sg.id,
        security_group_id=envoy_service_sg.id,
        description="Envoy service from ALB"
    )
    
    # Envoy metrics endpoint
    aws.ec2.SecurityGroupRule(
        "envoy_metrics",
        type="ingress",
        from_port=9901,
        to_port=9901,
        protocol="tcp",
        source_security_group_id=worker_node_sg.id,
        security_group_id=envoy_service_sg.id,
        description="Envoy metrics endpoint"
    )
    
    security_groups = {
        "eks_cluster": eks_cluster_sg,
        "worker_node": worker_node_sg,
        "alb": alb_sg,
        "envoy_service": envoy_service_sg
    }
    
    # Export security group IDs
    for name, sg in security_groups.items():
        pulumi.export(f"{name}_security_group_id", sg.id)
    
    return security_groups


def create_networking_infrastructure():
    """Main function to create all networking components"""
    
    # Get availability zones
    availability_zones = get_availability_zones()
    pulumi.export("availability_zones", availability_zones)
    
    # Create VPC
    vpc = create_vpc()
    
    # Create Internet Gateway
    igw = create_internet_gateway(vpc)
    
    # Create subnets
    public_subnets = create_public_subnets(vpc, availability_zones)
    private_subnets = create_private_subnets(vpc, availability_zones)
    
    # Create NAT Gateways
    nat_gateways = create_nat_gateways(public_subnets)
    
    # Create Route Tables
    route_tables = create_route_tables(vpc, igw, public_subnets, private_subnets, nat_gateways)
    
    # Create Security Groups
    security_groups = create_security_groups(vpc)
    
    return {
        "vpc": vpc,
        "public_subnets": public_subnets,
        "private_subnets": private_subnets,
        "security_groups": security_groups,
        "availability_zones": availability_zones
    }


if __name__ == "__main__":
    # Create the networking infrastructure
    infrastructure = create_networking_infrastructure()
    
    # Additional exports for use by other components
    pulumi.export("infrastructure_ready", True)
