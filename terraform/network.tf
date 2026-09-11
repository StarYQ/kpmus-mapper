# Firewall for the app instance: HTTP from anywhere, SSH from ssh_cidr, all egress.
resource "aws_security_group" "app" {
  name        = "${var.name}-app"
  description = "${var.name} application instance"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description = "HTTP"
    from_port   = 80
    to_port     = 80
    protocol    = "tcp"
    cidr_blocks = ["0.0.0.0/0"]
  }

  ingress {
    description = "SSH"
    from_port   = 22
    to_port     = 22
    protocol    = "tcp"
    cidr_blocks = [var.ssh_cidr]
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

# Firewall for the database: Postgres only from the app's security group. No public path.
resource "aws_security_group" "db" {
  name        = "${var.name}-db"
  description = "Postgres, reachable only from the app instance"
  vpc_id      = data.aws_vpc.default.id

  ingress {
    description     = "Postgres from the app instance"
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = [aws_security_group.app.id]
  }
}
