# scripts/deploy.sh reads these two to find the instance and build the database URLs.
output "app_ip" {
  value = aws_eip.app.public_ip
}

output "db_endpoint" {
  value = aws_db_instance.main.endpoint
}
