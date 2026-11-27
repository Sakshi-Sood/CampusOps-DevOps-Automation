locals {
  tags = {
    Project   = "CampusOps"
    ManagedBy = "Terraform"
  }
  hosts = toset(["app", "monitoring"])
}

resource "aws_vpc" "lab" {
  cidr_block           = "10.42.0.0/16"
  enable_dns_support   = true
  enable_dns_hostnames = true
  tags                 = merge(local.tags, { Name = "campusops-vpc" })
}

resource "aws_subnet" "public" {
  vpc_id     = aws_vpc.lab.id
  cidr_block = "10.42.1.0/24"
  tags       = merge(local.tags, { Name = "campusops-public" })
}

resource "aws_internet_gateway" "lab" {
  vpc_id = aws_vpc.lab.id
  tags   = merge(local.tags, { Name = "campusops-igw" })
}

resource "aws_route_table" "public" {
  vpc_id = aws_vpc.lab.id
  tags   = merge(local.tags, { Name = "campusops-public" })
}

resource "aws_route" "internet" {
  route_table_id         = aws_route_table.public.id
  destination_cidr_block = "0.0.0.0/0"
  gateway_id             = aws_internet_gateway.lab.id
}

resource "aws_route_table_association" "public" {
  subnet_id      = aws_subnet.public.id
  route_table_id = aws_route_table.public.id
}
