output "dashboard_url" {
  description = "Public dashboard."
  value       = "http://${aws_lb.main.dns_name}/dashboard/"
}

output "ecr_backend" {
  value = aws_ecr_repository.backend.repository_url
}

output "ecr_victim" {
  value = aws_ecr_repository.victim.repository_url
}

output "transcript_bucket" {
  description = "Tool-call transcripts — the evaluation corpus."
  value       = aws_s3_bucket.transcripts.id
}

output "remediation_state_machine" {
  value = aws_sfn_state_machine.remediation.arn
}

output "remediation_role_arn" {
  description = "The identity permitted to restart exactly one service, and nothing else."
  value       = aws_iam_role.remediation.arn
}

output "db_endpoint" {
  value = aws_db_instance.main.address
}
