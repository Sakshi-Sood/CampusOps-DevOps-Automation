output "hosts" {
  description = "SSH targets and private addresses for Ansible and Nagios."
  value = {
    for name, host in aws_instance.host : name => {
      instance_id = host.id
      public_ip   = host.public_ip
      private_ip  = host.private_ip
    }
  }
}

output "network" {
  description = "Identifiers for the CampusOps network."
  value = {
    vpc_id            = aws_vpc.lab.id
    subnet_id         = aws_subnet.public.id
    availability_zone = aws_subnet.public.availability_zone
    security_group_ids = {
      for name, group in aws_security_group.host : name => group.id
    }
  }
}
