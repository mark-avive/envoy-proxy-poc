"""
Main Pulumi program for Envoy Proxy POC AWS Infrastructure

This program creates the AWS networking infrastructure for the EKS cluster
and Envoy proxy setup according to the requirements.
"""

import pulumi
from networking import create_networking_infrastructure

def main():
    """Main function to deploy the infrastructure"""
    
    # Create networking infrastructure
    infrastructure = create_networking_infrastructure()
    
    # Output summary information
    pulumi.export("deployment_summary", {
        "vpc_name": "envoy-vpc",
        "vpc_cidr": "172.245.0.0/16",
        "public_subnets_count": 2,
        "private_subnets_count": 2,
        "nat_gateways_count": 2,
        "security_groups_count": 4,
        "project": "envoy-proxy-poc",
        "environment": "poc"
    })

if __name__ == "__main__":
    main()
