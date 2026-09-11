# Which subnets RDS may place the database in: the default VPC's subnets.
resource "aws_db_subnet_group" "main" {
  name       = var.name
  subnet_ids = data.aws_subnets.default.ids
}

# Managed Postgres. Smallest class; not publicly reachable; the app's security group is the only way in.
# skip_final_snapshot keeps `terraform destroy` clean while this is a dev stack.
resource "aws_db_instance" "main" {
  identifier             = var.name
  engine                 = "postgres"
  engine_version         = "17"
  instance_class         = "db.t4g.micro"
  allocated_storage      = 20
  storage_type           = "gp3"
  db_name                = var.db_name
  username               = var.db_username
  password               = var.db_password
  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false
  skip_final_snapshot    = true
}
