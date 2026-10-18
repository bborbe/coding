locals {
  retention_days = 30
}

# retention_days is the only knob an operator changes, so it lives at the top.
resource "aws_instance" "order_worker" {
  ami           = "ami-0123456789abcdef0"
  instance_type = "t3.micro"

  tags = {
    RetentionDays = local.retention_days
  }
}
