variable "aws_account_id" {
  description = "Approved 12-digit AWS account ID."
  type        = string
  nullable    = false
  validation {
    condition     = can(regex("^[0-9]{12}$", var.aws_account_id))
    error_message = "Provide a 12-digit AWS account ID."
  }
}

variable "ubuntu_ami_id" {
  description = "Reviewed Ubuntu 24.04 LTS amd64 AMI ID in Mumbai."
  type        = string
  nullable    = false
  validation {
    condition     = can(regex("^ami-[0-9a-f]{17}$", var.ubuntu_ami_id))
    error_message = "Provide a 17-hex-digit AMI ID."
  }
}

variable "admin_ipv4_cidr" {
  description = "Operator public IPv4 address with a /32 mask."
  type        = string
  nullable    = false
  validation {
    condition     = can(cidrnetmask(var.admin_ipv4_cidr)) && endswith(var.admin_ipv4_cidr, "/32")
    error_message = "Use one IPv4 address in /32 notation."
  }
}

variable "demo_ipv4_cidrs" {
  description = "Optional allowlist for demo HTTP."
  type        = set(string)
  default     = []
  nullable    = false
  validation {
    condition = alltrue([
      for cidr in var.demo_ipv4_cidrs : try(
        cidrnetmask(cidr) != "" && tonumber(split("/", cidr)[1]) >= 24 && cidrsubnet(cidr, 0, 0) == cidr,
        false
      )
    ])
    error_message = "Use canonical IPv4 networks with a /24 or narrower mask."
  }
}

variable "ssh_public_key_path" {
  description = "Path to a local OpenSSH Ed25519 public key file."
  type        = string
  nullable    = false
  validation {
    condition = try(
      endswith(var.ssh_public_key_path, ".pub") &&
      can(regex("^ssh-ed25519[ \t]+[A-Za-z0-9+/=]+([ \t]+[^\r\n]+)?$", trimspace(file(pathexpand(var.ssh_public_key_path))))),
      false
    )
    error_message = "Provide a readable .pub file containing one OpenSSH Ed25519 public key."
  }
}
