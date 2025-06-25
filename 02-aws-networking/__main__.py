"""
AWS Networking Infrastructure for Envoy Proxy POC
Requirement Section 2: VPC, Subnets, Security Groups, Internet Gateway, NAT Gateways
"""

import pulumi
import pulumi_aws as aws

# Get configuration values
config = pulumi.Config()
vpc_name = config.require("vpc_name")
vpc_cidr = config.require("vpc_cidr")
project_name = config.require("project_name")

# Get availability zones
azs = aws.get_availability_zones(state="available")

# Create VPC
envoy_poc_vpc = aws.ec2.Vpc(
    "envoy-poc-vpc",
    cidr_block=vpc_cidr,
    enable_dns_hostnames=True,
    enable_dns_support=True,
    tags={
        "Name": vpc_name,
        "Project": project_name,
        "Environment": "poc"
    }
)

# Create Internet Gateway
envoy_poc_igw = aws.ec2.InternetGateway(
    "envoy-poc-igw",
    vpc_id=envoy_poc_vpc.id,
    tags={
        "Name": f"{project_name}-igw",
        "Project": project_name
    }
)

# Create public subnets (2) in different AZs
public_subnet_1 = aws.ec2.Subnet(
    "envoy-poc-public-subnet-1",
    vpc_id=envoy_poc_vpc.id,
    cidr_block="172.245.1.0/24",
    availability_zone=azs.names[0],
    map_public_ip_on_launch=True,
    tags={
        "Name": f"{project_name}-public-subnet-1",
        "Project": project_name,
        "Type": "public"
    }
)

public_subnet_2 = aws.ec2.Subnet(
    "envoy-poc-public-subnet-2",
    vpc_id=envoy_poc_vpc.id,
    cidr_block="172.245.2.0/24",
    availability_zone=azs.names[1],
    map_public_ip_on_launch=True,
    tags={
        "Name": f"{project_name}-public-subnet-2",
        "Project": project_name,
        "Type": "public"
    }
)

# Create private subnets (2) in different AZs for EKS worker nodes
private_subnet_1 = aws.ec2.Subnet(
    "envoy-poc-private-subnet-1",
    vpc_id=envoy_poc_vpc.id,
    cidr_block="172.245.10.0/24",
    availability_zone=azs.names[0],
    tags={
        "Name": f"{project_name}-private-subnet-1",
        "Project": project_name,
        "Type": "private"
    }
)

private_subnet_2 = aws.ec2.Subnet(
    "envoy-poc-private-subnet-2",
    vpc_id=envoy_poc_vpc.id,
    cidr_block="172.245.11.0/24",
    availability_zone=azs.names[1],
    tags={
        "Name": f"{project_name}-private-subnet-2",
        "Project": project_name,
        "Type": "private"
    }
)

# Create Elastic IPs for NAT Gateways
nat_eip_1 = aws.ec2.Eip(
    "envoy-poc-nat-eip-1",
    domain="vpc",
    tags={
        "Name": f"{project_name}-nat-eip-1",
        "Project": project_name
    }
)

nat_eip_2 = aws.ec2.Eip(
    "envoy-poc-nat-eip-2",
    domain="vpc",
    tags={
        "Name": f"{project_name}-nat-eip-2",
        "Project": project_name
    }
)

# Create NAT Gateways (2) - one in each public subnet
nat_gateway_1 = aws.ec2.NatGateway(
    "envoy-poc-nat-gateway-1",
    allocation_id=nat_eip_1.id,
    subnet_id=public_subnet_1.id,
    tags={
        "Name": f"{project_name}-nat-gateway-1",
        "Project": project_name
    }
)

nat_gateway_2 = aws.ec2.NatGateway(
    "envoy-poc-nat-gateway-2",
    allocation_id=nat_eip_2.id,
    subnet_id=public_subnet_2.id,
    tags={
        "Name": f"{project_name}-nat-gateway-2",
        "Project": project_name
    }
)

# Create route table for public subnets
public_route_table = aws.ec2.RouteTable(
    "envoy-poc-public-rt",
    vpc_id=envoy_poc_vpc.id,
    tags={
        "Name": f"{project_name}-public-rt",
        "Project": project_name
    }
)

# Create route to Internet Gateway for public subnets
public_route = aws.ec2.Route(
    "envoy-poc-public-route",
    route_table_id=public_route_table.id,
    destination_cidr_block="0.0.0.0/0",
    gateway_id=envoy_poc_igw.id
)

# Associate public subnets with public route table
public_rt_association_1 = aws.ec2.RouteTableAssociation(
    "envoy-poc-public-rt-association-1",
    subnet_id=public_subnet_1.id,
    route_table_id=public_route_table.id
)

public_rt_association_2 = aws.ec2.RouteTableAssociation(
    "envoy-poc-public-rt-association-2",
    subnet_id=public_subnet_2.id,
    route_table_id=public_route_table.id
)

# Create route tables for private subnets (separate for each AZ)
private_route_table_1 = aws.ec2.RouteTable(
    "envoy-poc-private-rt-1",
    vpc_id=envoy_poc_vpc.id,
    tags={
        "Name": f"{project_name}-private-rt-1",
        "Project": project_name
    }
)

private_route_table_2 = aws.ec2.RouteTable(
    "envoy-poc-private-rt-2",
    vpc_id=envoy_poc_vpc.id,
    tags={
        "Name": f"{project_name}-private-rt-2",
        "Project": project_name
    }
)

# Create routes to NAT Gateways for private subnets
private_route_1 = aws.ec2.Route(
    "envoy-poc-private-route-1",
    route_table_id=private_route_table_1.id,
    destination_cidr_block="0.0.0.0/0",
    nat_gateway_id=nat_gateway_1.id
)

private_route_2 = aws.ec2.Route(
    "envoy-poc-private-route-2",
    route_table_id=private_route_table_2.id,
    destination_cidr_block="0.0.0.0/0",
    nat_gateway_id=nat_gateway_2.id
)

# Associate private subnets with their respective route tables
private_rt_association_1 = aws.ec2.RouteTableAssociation(
    "envoy-poc-private-rt-association-1",
    subnet_id=private_subnet_1.id,
    route_table_id=private_route_table_1.id
)

private_rt_association_2 = aws.ec2.RouteTableAssociation(
    "envoy-poc-private-rt-association-2",
    subnet_id=private_subnet_2.id,
    route_table_id=private_route_table_2.id
)

# Security Group for EKS Cluster
envoy_poc_eks_cluster_sg = aws.ec2.SecurityGroup(
    "envoy-poc-eks-cluster-sg",
    name=f"{project_name}-eks-cluster-sg",
    description="Security group for EKS cluster control plane communication with worker nodes",
    vpc_id=envoy_poc_vpc.id,
    tags={
        "Name": f"{project_name}-eks-cluster-sg",
        "Project": project_name
    }
)

# Security Group for EKS Worker Nodes
envoy_poc_worker_node_sg = aws.ec2.SecurityGroup(
    "envoy-poc-worker-node-sg",
    name=f"{project_name}-worker-node-sg",
    description="Security group for EKS worker nodes",
    vpc_id=envoy_poc_vpc.id,
    tags={
        "Name": f"{project_name}-worker-node-sg",
        "Project": project_name
    }
)

# Security Group for ALB
envoy_poc_alb_sg = aws.ec2.SecurityGroup(
    "envoy-poc-alb-sg",
    name=f"{project_name}-alb-sg",
    description="Security group for Application Load Balancer",
    vpc_id=envoy_poc_vpc.id,
    ingress=[{
        "protocol": "tcp",
        "from_port": 80,
        "to_port": 80,
        "cidr_blocks": ["0.0.0.0/0"],
        "description": "HTTP traffic from internet"
    }],
    egress=[{
        "protocol": "-1",
        "from_port": 0,
        "to_port": 0,
        "cidr_blocks": ["0.0.0.0/0"],
        "description": "All outbound traffic"
    }],
    tags={
        "Name": f"{project_name}-alb-sg",
        "Project": project_name
    }
)

# Security Group for Envoy Service
envoy_poc_envoy_service_sg = aws.ec2.SecurityGroup(
    "envoy-poc-envoy-service-sg",
    name=f"{project_name}-envoy-service-sg",
    description="Security group for Envoy proxy service",
    vpc_id=envoy_poc_vpc.id,
    tags={
        "Name": f"{project_name}-envoy-service-sg",
        "Project": project_name
    }
)

# Security Group Rules for EKS Cluster and Worker Node communication
# Allow worker nodes to communicate with cluster API server
cluster_ingress_worker_https = aws.ec2.SecurityGroupRule(
    "envoy-poc-cluster-ingress-worker-https",
    type="ingress",
    from_port=443,
    to_port=443,
    protocol="tcp",
    source_security_group_id=envoy_poc_worker_node_sg.id,
    security_group_id=envoy_poc_eks_cluster_sg.id,
    description="Allow worker nodes to communicate with cluster API server"
)

# Allow pods to communicate with cluster API server
cluster_ingress_worker_kubelet = aws.ec2.SecurityGroupRule(
    "envoy-poc-cluster-ingress-worker-kubelet",
    type="ingress",
    from_port=10250,
    to_port=10250,
    protocol="tcp",
    source_security_group_id=envoy_poc_worker_node_sg.id,
    security_group_id=envoy_poc_eks_cluster_sg.id,
    description="Allow worker Kubelet and pods to receive communication from cluster"
)

# Allow worker nodes to receive communication from cluster
worker_ingress_cluster = aws.ec2.SecurityGroupRule(
    "envoy-poc-worker-ingress-cluster",
    type="ingress",
    from_port=1025,
    to_port=65535,
    protocol="tcp",
    source_security_group_id=envoy_poc_eks_cluster_sg.id,
    security_group_id=envoy_poc_worker_node_sg.id,
    description="Allow worker nodes to receive communication from cluster"
)

# Allow worker nodes to communicate among themselves
worker_ingress_self = aws.ec2.SecurityGroupRule(
    "envoy-poc-worker-ingress-self",
    type="ingress",
    from_port=0,
    to_port=65535,
    protocol="-1",
    source_security_group_id=envoy_poc_worker_node_sg.id,
    security_group_id=envoy_poc_worker_node_sg.id,
    description="Allow worker nodes to communicate among themselves"
)

# Allow worker nodes outbound internet access
worker_egress_internet = aws.ec2.SecurityGroupRule(
    "envoy-poc-worker-egress-internet",
    type="egress",
    from_port=0,
    to_port=0,
    protocol="-1",
    cidr_blocks=["0.0.0.0/0"],
    security_group_id=envoy_poc_worker_node_sg.id,
    description="Allow worker nodes outbound internet access"
)

# Allow ALB to communicate with Envoy service
envoy_ingress_alb = aws.ec2.SecurityGroupRule(
    "envoy-poc-envoy-ingress-alb",
    type="ingress",
    from_port=80,
    to_port=80,
    protocol="tcp",
    source_security_group_id=envoy_poc_alb_sg.id,
    security_group_id=envoy_poc_envoy_service_sg.id,
    description="Allow ALB to communicate with Envoy service"
)

# Export important resource information for use by other stacks
pulumi.export("vpc_id", envoy_poc_vpc.id)
pulumi.export("vpc_cidr", envoy_poc_vpc.cidr_block)
pulumi.export("public_subnet_ids", [public_subnet_1.id, public_subnet_2.id])
pulumi.export("private_subnet_ids", [private_subnet_1.id, private_subnet_2.id])
pulumi.export("public_subnet_1_id", public_subnet_1.id)
pulumi.export("public_subnet_2_id", public_subnet_2.id)
pulumi.export("private_subnet_1_id", private_subnet_1.id)
pulumi.export("private_subnet_2_id", private_subnet_2.id)
pulumi.export("internet_gateway_id", envoy_poc_igw.id)
pulumi.export("nat_gateway_1_id", nat_gateway_1.id)
pulumi.export("nat_gateway_2_id", nat_gateway_2.id)
pulumi.export("eks_cluster_sg_id", envoy_poc_eks_cluster_sg.id)
pulumi.export("worker_node_sg_id", envoy_poc_worker_node_sg.id)
pulumi.export("alb_sg_id", envoy_poc_alb_sg.id)
pulumi.export("envoy_service_sg_id", envoy_poc_envoy_service_sg.id)
pulumi.export("availability_zones", azs.names)
