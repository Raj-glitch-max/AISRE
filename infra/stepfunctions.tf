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

data "archive_file" "remediate" {
  type        = "zip"
  output_path = "${path.module}/build/remediate.zip"

  source {
    filename = "index.py"
    content  = <<-PY
      import os
      import boto3

      ecs = boto3.client("ecs")

      CLUSTER = os.environ["CLUSTER"]
      SERVICE = os.environ["SERVICE"]


      def handler(event, context):
          """Force a new deployment. This is the entire action space of this identity —
          IAM permits UpdateService on one service ARN and denies a task-definition
          change, so this function cannot deploy different code even if asked to."""
          ecs.update_service(
              cluster=CLUSTER,
              service=SERVICE,
              forceNewDeployment=True,
          )
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
  timeout          = 30

  environment {
    variables = {
      CLUSTER = aws_ecs_cluster.main.name
      SERVICE = aws_ecs_service.victim.name
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
        Next     = "Verify"
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

      # The restart is asynchronous; give the service time to come back before judging.
      Verify = {
        Type    = "Wait"
        Seconds = 30
        Next    = "Done"
      }

      Done              = { Type = "Succeed" }
      ApprovalExpired   = { Type = "Fail", Error = "ApprovalExpired", Cause = "No human approval within the timeout; fail closed." }
      RemediationFailed = { Type = "Fail", Error = "RemediationFailed", Cause = "The fixed action did not complete." }
    }
  })
}
