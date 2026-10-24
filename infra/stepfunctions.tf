# The approval gate, modelled explicitly rather than living inside application code.
#
# Why this is worth the file: in the laptop version, "wait for a human, then act" is a
# status column and a FastAPI route. Here it is a state machine with a durable
# task token — the workflow survives a backend restart mid-incident, the human callback
# has an enforced timeout, and the transition into the acting state is the single audited
# point where authority changes hands. That is the same property Atlas provides at the
# application layer, expressed in infrastructure.

resource "aws_sns_topic" "approvals" {
  name = "${local.name}-approvals"
}

resource "aws_sns_topic_subscription" "approvals_email" {
  count     = var.alert_email != "" ? 1 : 0
  topic_arn = aws_sns_topic.approvals.arn
  protocol  = "email"
  endpoint  = var.alert_email
}

# Health check Lambda - verifies service health after restart
data "archive_file" "health_check" {
  type        = "zip"
  output_path = "${path.module}/build/health_check.zip"

  source {
    filename = "health_check.py"
    content  = <<-PY
      import os
      import json
      import urllib.request
      import urllib.error

      HEALTH_URL = os.environ.get("HEALTH_URL", "http://localhost:8000/health")
      MAX_ATTEMPTS = int(os.environ.get("MAX_ATTEMPTS", "3"))
      RETRY_INTERVAL = int(os.environ.get("RETRY_INTERVAL", "10"))

      def handler(event, context):
          """Check victim service health with retries."""
          for attempt in range(1, MAX_ATTEMPTS + 1):
              try:
                  req = urllib.request.Request(HEALTH_URL, method="GET")
                  with urllib.request.urlopen(req, timeout=5) as resp:
                      if resp.status == 200:
                          return {"healthy": True, "attempt": attempt}
              except urllib.error.URLError:
                  pass
              except urllib.error.HTTPError:
                  pass

              if attempt < MAX_ATTEMPTS:
                  import time
                  time.sleep(RETRY_INTERVAL)

          return {"healthy": False, "attempts": MAX_ATTEMPTS}
    PY
  }
}

resource "aws_lambda_function" "health_check" {
  function_name    = "${local.name}-health-check"
  role             = aws_iam_role.health_check.arn
  handler          = "health_check.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.health_check.output_path
  source_code_hash = data.archive_file.health_check.output_base64sha256
  timeout          = 60

  environment {
    variables = {
      HEALTH_URL      = "http://${aws_lb.victim.dns_name}/health"
      MAX_ATTEMPTS    = "3"
      RETRY_INTERVAL  = "10"
    }
  }
}

# Remediation Lambda - with Atlas capability verification
data "archive_file" "remediate" {
  type        = "zip"
  output_path = "${path.module}/build/remediate.zip"

  source {
    filename = "index.py"
    content  = <<-PY
      import os
      import json
      import urllib.request
      import urllib.error
      import boto3

      CLUSTER = os.environ["CLUSTER"]
      SERVICE = os.environ["SERVICE"]
      ATLAS_URL = os.environ["ATLAS_URL"]
      ATLAS_API_KEY = os.environ.get("ATLAS_API_KEY")
      ATLAS_PRINCIPAL = os.environ["ATLAS_PRINCIPAL"]
      ATLAS_DELEGATE = os.environ["ATLAS_DELEGATE"]
      VICTIM_CONTAINER = os.environ.get("VICTIM_CONTAINER", "victim-app")

      ecs = boto3.client("ecs")

      def _call_atlas(method, path, body=None):
          """Call Atlas server."""
          data = json.dumps(body).encode() if body is not None else None
          req = urllib.request.Request(ATLAS_URL + path, data=data, method=method)
          req.add_header("Content-Type", "application/json")
          if ATLAS_API_KEY:
              req.add_header("Authorization", "Bearer " + ATLAS_API_KEY)
          try:
              with urllib.request.urlopen(req, timeout=8) as resp:
                  return json.loads(resp.read())
          except urllib.error.HTTPError as e:
              raw = e.read()
              try:
                  msg = json.loads(raw).get("error", raw.decode())
              except Exception:
                  msg = raw.decode(errors="replace")
              raise RuntimeError(f"{e.code}: {msg}")
          except urllib.error.URLError as e:
              raise RuntimeError(f"atlas-server unreachable ({e.reason})")

      def handler(event, context):
          """Force a new deployment after verifying Atlas capability."""
          # Step 1: Issue capability
          grant = _call_atlas("POST", "/issue", {
              "principal": ATLAS_PRINCIPAL,
              "delegate": ATLAS_DELEGATE,
              "scope": [f"remediate:restart:{VICTIM_CONTAINER}"],
              "ttlSeconds": 120,
          })

          # Step 2: Verify capability
          result = _call_atlas("POST", "/verify", {"record": grant["record"]})
          if result.get("decision") != "accept":
              _call_atlas("POST", "/revoke", {"instance": grant["instance"]})
              raise RuntimeError(f"capability rejected: {result.get('decision')}")

          # Step 3: Execute restart
          ecs.update_service(
              cluster=CLUSTER,
              service=SERVICE,
              forceNewDeployment=True,
          )

          # Step 4: Revoke capability
          try:
              _call_atlas("POST", "/revoke", {"instance": grant["instance"]})
          except Exception:
              pass  # Non-fatal, expires in ~150s

          return {"restarted": SERVICE, "incident_id": event.get("incident_id")}
    PY
  }
}

resource "aws_lambda_function" "remediate" {
  function_name    = "${local.name}-remediate"
  role             = aws_iam_role.remediation.arn
  handler          = "index.handler"
  runtime          = "python3.12"
  filename         = data.archive_file.remediate.output_path
  source_code_hash = data.archive_file.remediate.output_base64sha256
  timeout          = 60

  environment {
    variables = {
      CLUSTER           = aws_ecs_cluster.main.name
      SERVICE           = aws_ecs_service.victim.name
      ATLAS_URL         = var.atlas_url
      ATLAS_API_KEY     = var.atlas_api_key
      ATLAS_PRINCIPAL   = var.atlas_principal
      ATLAS_DELEGATE    = var.atlas_delegate
      VICTIM_CONTAINER  = "victim-app"
    }
  }
}

resource "aws_sfn_state_machine" "remediation" {
  name     = "${local.name}-remediation"
  role_arn = aws_iam_role.stepfunctions.arn

  definition = jsonencode({
    Comment = "Investigate -> human approval -> Atlas-gated fixed action -> verify"
    StartAt = "RequestApproval"

    States = {
      # waitForTaskToken: the execution parks here durably until a human responds.
      RequestApproval = {
        Type     = "Task"
        Resource = "arn:aws:states:::sns:publish.waitForTaskToken"
        Parameters = {
          TopicArn = aws_sns_topic.approvals.arn
          Message = {
            "incident_id.$" = "$.incident_id"
            "root_cause.$"  = "$.root_cause"
            "note"          = "Approve to restart victim-app. The action is fixed; the model's recommended_action is not executed."
            "taskToken.$"   = "$$.Task.Token"
          }
        }
        TimeoutSeconds = 3600
        Next           = "Remediate"
        Catch = [{
          ErrorEquals = ["States.Timeout"]
          Next        = "ApprovalExpired"
        }]
      }

      Remediate = {
        Type     = "Task"
        Resource = aws_lambda_function.remediate.arn
        Next     = "VerifyHealth"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 5
          MaxAttempts     = 2
          BackoffRate     = 2.0
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "RemediationFailed"
        }]
      }

      # Verify health with actual health checks, not just wait
      VerifyHealth = {
        Type     = "Task"
        Resource = aws_lambda_function.health_check.arn
        Next     = "CheckHealthResult"
        Retry = [{
          ErrorEquals     = ["States.TaskFailed"]
          IntervalSeconds = 10
          MaxAttempts     = 2
          BackoffRate     = 2.0
        }]
        Catch = [{
          ErrorEquals = ["States.ALL"]
          Next        = "RemediationFailed"
        }]
      }

      CheckHealthResult = {
        Type = "Choice"
        Choices = [{
          Variable = "$.healthy"
          BooleanEquals = true
          Next = "Done"
        }]
        Default = "RemediationFailed"
      }

      Done              = { Type = "Succeed" }
      ApprovalExpired   = { Type = "Fail", Error = "ApprovalExpired", Cause = "No human approval within the timeout; fail closed." }
      RemediationFailed = { Type = "Fail", Error = "RemediationFailed", Cause = "The fixed action did not complete or service remains unhealthy." }
    }
  })
}