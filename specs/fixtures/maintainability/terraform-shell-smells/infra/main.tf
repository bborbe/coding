resource "aws_instance" "order_worker" {
  ami = "ami-0123456789abcdef0"
  # set the instance type to t3.micro
  instance_type = "t3.micro"
}

locals {
  legacy_order_batch_size = 50
}
