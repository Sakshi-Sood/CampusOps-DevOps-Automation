provider "aws" {
  region              = "ap-south-1"
  profile             = "campusops-operator"
  allowed_account_ids = [var.aws_account_id]

  assume_role {
    role_arn     = "arn:aws:iam::${var.aws_account_id}:role/CampusOpsTerraformRole"
    session_name = "CampusOpsTerraform"
  }
}
