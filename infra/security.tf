locals {
  web_ports = { http = 80, https = 443 }
  web_egress = {
    for rule in setproduct(local.hosts, keys(local.web_ports)) :
    "${rule[0]}-${rule[1]}" => { host = rule[0], port = local.web_ports[rule[1]] }
  }
  checks = { ssh = 22, http = 80 }
}

resource "aws_security_group" "host" {
  for_each = local.hosts

  name        = "campusops-${each.key}"
  description = "CampusOps ${each.key} server access"
  vpc_id      = aws_vpc.lab.id
  tags        = merge(local.tags, { Name = "campusops-${each.key}" })
}

resource "aws_vpc_security_group_ingress_rule" "operator_ssh" {
  for_each = local.hosts

  security_group_id = aws_security_group.host[each.key].id
  description       = "Operator SSH"
  cidr_ipv4         = var.admin_ipv4_cidr
  ip_protocol       = "tcp"
  from_port         = 22
  to_port           = 22
  tags              = local.tags
}

resource "aws_vpc_security_group_ingress_rule" "demo_http" {
  for_each = var.demo_ipv4_cidrs

  security_group_id = aws_security_group.host["app"].id
  description       = "Approved HTTP demo access"
  cidr_ipv4         = each.value
  ip_protocol       = "tcp"
  from_port         = 80
  to_port           = 80
  tags              = local.tags
}

resource "aws_vpc_security_group_ingress_rule" "private_checks" {
  for_each = local.checks

  security_group_id            = aws_security_group.host["app"].id
  referenced_security_group_id = aws_security_group.host["monitoring"].id
  description                  = "Private monitoring ${each.key}"
  ip_protocol                  = "tcp"
  from_port                    = each.value
  to_port                      = each.value
  tags                         = local.tags
}

resource "aws_vpc_security_group_egress_rule" "web" {
  for_each = local.web_egress

  security_group_id = aws_security_group.host[each.value.host].id
  description       = "Package downloads and updates"
  cidr_ipv4         = "0.0.0.0/0"
  ip_protocol       = "tcp"
  from_port         = each.value.port
  to_port           = each.value.port
  tags              = local.tags
}

resource "aws_vpc_security_group_egress_rule" "private_ssh" {
  security_group_id            = aws_security_group.host["monitoring"].id
  referenced_security_group_id = aws_security_group.host["app"].id
  description                  = "Private SSH metrics and reachability"
  ip_protocol                  = "tcp"
  from_port                    = 22
  to_port                      = 22
  tags                         = local.tags
}
