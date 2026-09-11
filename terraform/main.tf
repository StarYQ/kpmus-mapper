# The AWS provider. Every resource is tagged Project=pmus-kalshi-mapper so the account's
# cost explorer and console filters find all of it in one query.
provider "aws" {
  region = var.region
  default_tags {
    tags = {
      Project = "pmus-kalshi-mapper"
    }
  }
}

# A fresh account has a default VPC in every region with one public subnet per AZ.
# That is all this deployment needs: the app instance sits in a public subnet with a
# public IP, the database sits in the same VPC and is reachable only from the app.
data "aws_vpc" "default" {
  default = true
}

data "aws_subnets" "default" {
  filter {
    name   = "vpc-id"
    values = [data.aws_vpc.default.id]
  }
}
