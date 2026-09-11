# The public half of the deploy key. The private half stays in ~/.ssh and is used by scripts/deploy.sh.
resource "aws_key_pair" "deploy" {
  key_name   = var.name
  public_key = file(pathexpand(var.public_key_path))
}

# Newest Amazon Linux 2023 image for x86_64 (t3 instances are x86_64).
data "aws_ami" "al2023" {
  most_recent = true
  owners      = ["amazon"]
  filter {
    name   = "name"
    values = ["al2023-ami-2023.*-x86_64"]
  }
}

# The one instance that runs the API container. First boot installs docker and rsync so
# scripts/deploy.sh can mirror the repo and build the image; ec2-user joins the docker group
# so the remote deploy script can call docker without sudo.
resource "aws_instance" "app" {
  ami                         = data.aws_ami.al2023.id
  instance_type               = var.instance_type
  key_name                    = aws_key_pair.deploy.key_name
  vpc_security_group_ids      = [aws_security_group.app.id]
  associate_public_ip_address = true

  root_block_device {
    volume_size = var.root_volume_gb
    volume_type = "gp3"
  }

  user_data = <<-EOF
    #!/bin/bash
    dnf install -y docker rsync git
    systemctl enable --now docker
    usermod -aG docker ec2-user
  EOF

  tags = {
    Name = "${var.name}-app"
  }
}

# A fixed public IP, so stop/start of the instance never changes the address deploy.sh targets.
resource "aws_eip" "app" {
  instance = aws_instance.app.id
  domain   = "vpc"
  tags = {
    Name = "${var.name}-app"
  }
}
