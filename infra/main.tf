data "aws_ami" "ubuntu" {
  owners = ["099720109477"] # Canonical's public publisher account.

  filter {
    name   = "image-id"
    values = [var.ubuntu_ami_id]
  }

  filter {
    name   = "name"
    values = ["ubuntu/images/hvm-ssd-gp3/ubuntu-noble-24.04-amd64-server-*"]
  }

  filter {
    name   = "architecture"
    values = ["x86_64"]
  }

  filter {
    name   = "state"
    values = ["available"]
  }
}

resource "aws_key_pair" "operator" {
  key_name = "campusops-operator"
  # Omit comments that might contain a username or hostname.
  public_key = join(" ", slice(regexall("\\S+", trimspace(file(pathexpand(var.ssh_public_key_path)))), 0, 2))
  tags       = merge(local.tags, { Name = "campusops-operator" })
}

resource "aws_instance" "host" {
  for_each = local.hosts

  ami                         = data.aws_ami.ubuntu.id
  instance_type               = "t3.micro"
  subnet_id                   = aws_subnet.public.id
  vpc_security_group_ids      = [aws_security_group.host[each.key].id]
  associate_public_ip_address = true
  key_name                    = aws_key_pair.operator.key_name

  credit_specification {
    cpu_credits = "standard"
  }

  metadata_options {
    http_endpoint = "enabled"
    http_tokens   = "required"
  }

  root_block_device {
    encrypted             = true
    volume_type           = "gp3"
    volume_size           = 10
    delete_on_termination = true
  }

  tags        = merge(local.tags, { Name = "campusops-${each.key}", Role = each.key })
  volume_tags = merge(local.tags, { Name = "campusops-${each.key}-root", Role = each.key })

  depends_on = [aws_route.internet, aws_route_table_association.public]
}
