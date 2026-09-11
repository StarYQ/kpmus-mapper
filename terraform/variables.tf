variable "region" {
  description = "AWS region for everything here"
  default     = "us-east-2"
}

variable "name" {
  description = "Prefix for every resource name and the ssh key pair"
  default     = "pmus-kalshi-mapper"
}

# The mapper is light: the full PMUS capture is ~140 MB and a full-surface resolve takes 17 s.
# 2 vCPU / 2 GB is enough for gunicorn + the docker build of the React bundle.
variable "instance_type" {
  default = "t3.small"
}

variable "root_volume_gb" {
  description = "Root disk. Captures are ~140 MB each; 30 GB leaves room for docker layers and a few captures"
  default     = 30
}

variable "db_name" {
  default = "mapper"
}

variable "db_username" {
  default = "mapper"
}

# No default on purpose. Lives in terraform/terraform.tfvars (gitignored); scripts/deploy.sh reads
# the same file to build the connection strings.
variable "db_password" {
  type      = string
  sensitive = true
}

# Who may reach port 22. Narrow it to your own IP ("1.2.3.4/32") once you know it.
variable "ssh_cidr" {
  default = "0.0.0.0/0"
}

# Public half of the key scripts/deploy.sh uses. Generate with:
#   ssh-keygen -t ed25519 -N "" -f ~/.ssh/id_ed25519_pmus-kalshi-mapper
variable "public_key_path" {
  default = "~/.ssh/id_ed25519_pmus-kalshi-mapper.pub"
}
