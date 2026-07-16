variable "environment" { type = string }
variable "vpc_id" { type = string }
variable "private_subnet_ids" { type = list(string) }
variable "allowed_security_groups" { type = list(string) }
variable "instance_class" { type = string }
variable "allocated_storage_gb" { type = number }
variable "database_name" { type = string }
variable "master_username" { type = string }

resource "random_password" "master" {
  length  = 32
  special = false
}

resource "aws_db_subnet_group" "this" {
  name       = "gie-${var.environment}-postgres"
  subnet_ids = var.private_subnet_ids

  tags = {
    Name = "gie-${var.environment}-postgres-subnet-group"
  }
}

resource "aws_security_group" "postgres" {
  name        = "gie-${var.environment}-postgres"
  description = "PostgreSQL access from app tier"
  vpc_id      = var.vpc_id

  ingress {
    from_port       = 5432
    to_port         = 5432
    protocol        = "tcp"
    security_groups = var.allowed_security_groups
  }

  egress {
    from_port   = 0
    to_port     = 0
    protocol    = "-1"
    cidr_blocks = ["0.0.0.0/0"]
  }
}

resource "aws_db_instance" "this" {
  identifier                 = "gie-${var.environment}-context"
  engine                     = "postgres"
  engine_version             = "16.4"
  instance_class             = var.instance_class
  allocated_storage          = var.allocated_storage_gb
  storage_type               = "gp3"
  storage_encrypted          = true
  db_name                    = var.database_name
  username                   = var.master_username
  password                   = random_password.master.result
  db_subnet_group_name       = aws_db_subnet_group.this.name
  vpc_security_group_ids     = [aws_security_group.postgres.id]
  multi_az                   = var.environment == "production"
  backup_retention_period    = var.environment == "production" ? 14 : 3
  skip_final_snapshot        = var.environment != "production"
  deletion_protection        = var.environment == "production"
  auto_minor_version_upgrade = true
  performance_insights_enabled = true

  tags = {
    Name = "gie-${var.environment}-context-postgres"
  }
}

resource "aws_secretsmanager_secret" "credentials" {
  name = "gie/${var.environment}/context-intelligence/postgres"
}

resource "aws_secretsmanager_secret_version" "credentials" {
  secret_id = aws_secretsmanager_secret.credentials.id
  secret_string = jsonencode({
    username = var.master_username
    password = random_password.master.result
    host     = aws_db_instance.this.address
    port     = aws_db_instance.this.port
    dbname   = var.database_name
  })
}

output "endpoint" {
  value = "${aws_db_instance.this.address}:${aws_db_instance.this.port}"
}

output "connection_string_template" {
  value = "postgresql+asyncpg://${var.master_username}:<password>@${aws_db_instance.this.address}:${aws_db_instance.this.port}/${var.database_name}"
}

output "secret_arn" {
  value = aws_secretsmanager_secret.credentials.arn
}
