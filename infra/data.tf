# --- transcript / RCA storage ---
#
# The tool-call transcripts are the evaluation corpus (see eval/RESULTS.md). They are the
# one thing here worth keeping after a teardown, hence the lifecycle block.

resource "aws_s3_bucket" "transcripts" {
  bucket = "${local.name}-transcripts-${data.aws_caller_identity.current.account_id}"

  # force_destroy allows `terraform destroy` to remove the bucket with objects still in
  # it. This previously carried prevent_destroy to protect the evaluation corpus; that
  # blocked teardown of a stack being run on a personal account, and the corpus that
  # actually matters lives in eval/results/ and backend/incidents.db, both in git.
  # Re-add prevent_destroy if this ever holds the only copy of anything.
  force_destroy = true
}

resource "aws_s3_bucket_public_access_block" "transcripts" {
  bucket                  = aws_s3_bucket.transcripts.id
  block_public_acls       = true
  block_public_policy     = true
  ignore_public_acls      = true
  restrict_public_buckets = true
}

resource "aws_s3_bucket_versioning" "transcripts" {
  bucket = aws_s3_bucket.transcripts.id
  versioning_configuration {
    status = "Enabled"
  }
}

resource "aws_s3_bucket_server_side_encryption_configuration" "transcripts" {
  bucket = aws_s3_bucket.transcripts.id
  rule {
    apply_server_side_encryption_by_default {
      sse_algorithm = "AES256"
    }
  }
}

# --- secrets ---

resource "random_password" "db" {
  length  = 32
  special = false
}

resource "aws_secretsmanager_secret" "db" {
  name                    = "${local.name}/db"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "db" {
  secret_id = aws_secretsmanager_secret.db.id
  secret_string = jsonencode({
    username = "aisre"
    password = random_password.db.result
    dbname   = "aisre"
  })
}

resource "aws_secretsmanager_secret" "nim_key" {
  name                    = "${local.name}/nim-api-key"
  recovery_window_in_days = 0
}

resource "aws_secretsmanager_secret_version" "nim_key" {
  secret_id     = aws_secretsmanager_secret.nim_key.id
  secret_string = var.nim_api_key
}

# --- database ---
#
# SQLite was fine on a laptop and is a red flag in a deployed system: no concurrent
# writers, no durability story, nothing to point an interviewer at. Postgres also makes
# the transcript/RCA tables queryable for the evaluation work.

resource "aws_db_subnet_group" "main" {
  name       = "${local.name}-db"
  subnet_ids = aws_subnet.private[*].id
}

resource "aws_db_instance" "main" {
  identifier     = "${local.name}-db"
  engine         = "postgres"
  engine_version = "16.4"
  instance_class = var.db_instance_class

  allocated_storage     = 20
  max_allocated_storage = 50
  storage_type          = "gp3"
  storage_encrypted     = true

  db_name  = "aisre"
  username = "aisre"
  password = random_password.db.result

  db_subnet_group_name   = aws_db_subnet_group.main.name
  vpc_security_group_ids = [aws_security_group.db.id]
  publicly_accessible    = false

  backup_retention_period = 1
  skip_final_snapshot     = true
  apply_immediately       = true

  performance_insights_enabled = false
  auto_minor_version_upgrade   = true

  tags = { Name = "${local.name}-db" }
}
