variable "project" {
  type    = string
  default = "ai-sre"
}

variable "environment" {
  type    = string
  default = "dev"
}

variable "region" {
  type    = string
  default = "us-east-1"
}

variable "vpc_cidr" {
  type    = string
  default = "10.20.0.0/16"
}

variable "nim_api_key" {
  description = "NVIDIA NIM API key. Supply via TF_VAR_nim_api_key; never commit."
  type        = string
  sensitive   = true
}

variable "atlas_url" {
  description = "Base URL of the Atlas capability server that gates remediation."
  type        = string
  default     = "https://atlas-production-c457.up.railway.app"
}

variable "db_instance_class" {
  type    = string
  default = "db.t4g.micro"
}

variable "backend_image" {
  description = "ECR image URI for the AI-SRE backend. Set after the first push."
  type        = string
  default     = ""
}

variable "victim_image" {
  description = "ECR image URI for victim-app."
  type        = string
  default     = ""
}

variable "budget_monthly_usd" {
  description = "Monthly budget threshold that triggers an alarm."
  type        = number
  default     = 50
}

variable "alert_email" {
  description = "Address for budget and incident alarms. Empty disables subscriptions."
  type        = string
  default     = ""
}
