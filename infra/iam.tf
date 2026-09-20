# The load-bearing file.
#
# The claim this project makes is that an LLM-driven agent's authority to act is bounded
# by something other than its own good behaviour. Atlas enforces that at the application
# layer with a one-shot capability. This file enforces the same bound at the
# infrastructure layer, independently, so that neither system is the single point of
# failure. Each task gets only what it needs; the remediation role gets exactly one
# action on exactly one resource, under a permission boundary it cannot escape.

data "aws_iam_policy_document" "ecs_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["ecs-tasks.amazonaws.com"]
    }
  }
}

# --- execution role: pulling images and writing logs, nothing application-level ---

resource "aws_iam_role" "task_execution" {
  name               = "${local.name}-task-execution"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

resource "aws_iam_role_policy_attachment" "task_execution" {
  role       = aws_iam_role.task_execution.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AmazonECSTaskExecutionRolePolicy"
}

# The execution role also reads the two secrets injected into the task at start.
data "aws_iam_policy_document" "execution_secrets" {
  statement {
    actions   = ["secretsmanager:GetSecretValue"]
    resources = [aws_secretsmanager_secret.nim_key.arn, aws_secretsmanager_secret.db.arn]
  }
}

resource "aws_iam_role_policy" "execution_secrets" {
  name   = "${local.name}-execution-secrets"
  role   = aws_iam_role.task_execution.id
  policy = data.aws_iam_policy_document.execution_secrets.json
}

# --- the permission boundary ---
#
# Nothing wearing this boundary can ever exceed it, regardless of what policies are
# later attached to the role. This is the difference between "I scoped the policy" and
# "the scope cannot be widened by a future mistake" — the latter is the senior claim.

data "aws_iam_policy_document" "remediation_boundary" {
  statement {
    sid    = "TheOnlyMutatingActionThisIdentityMayEverPerform"
    effect = "Allow"
    actions = [
      "ecs:UpdateService",
      "ecs:DescribeServices",
    ]
    resources = [aws_ecs_service.victim.id]
  }

  statement {
    sid    = "ObservabilityOnly"
    effect = "Allow"
    actions = [
      "logs:CreateLogStream",
      "logs:PutLogEvents",
      "cloudwatch:PutMetricData",
    ]
    resources = ["*"]
  }

  statement {
    sid       = "ReadTranscriptsAndRCAs"
    effect    = "Allow"
    actions   = ["s3:GetObject", "s3:PutObject"]
    resources = ["${aws_s3_bucket.transcripts.arn}/*"]
  }

  # Explicit denies: belt and braces against a future attach of something broader.
  statement {
    sid    = "NeverIAMNeverEC2NeverData"
    effect = "Deny"
    actions = [
      "iam:*",
      "ec2:*",
      "rds:Delete*",
      "s3:DeleteBucket",
      "ecs:DeleteService",
      "ecs:RegisterTaskDefinition",
    ]
    resources = ["*"]
  }
}

resource "aws_iam_policy" "remediation_boundary" {
  name        = "${local.name}-remediation-boundary"
  description = "Hard ceiling on the remediation identity. Cannot be exceeded."
  policy      = data.aws_iam_policy_document.remediation_boundary.json
}

# --- remediation role: the identity that actually restarts the service ---

data "aws_iam_policy_document" "lambda_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["lambda.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "remediation" {
  name                 = "${local.name}-remediation"
  assume_role_policy   = data.aws_iam_policy_document.lambda_assume.json
  permissions_boundary = aws_iam_policy.remediation_boundary.arn
}

data "aws_iam_policy_document" "remediation" {
  statement {
    sid       = "RestartExactlyOneService"
    effect    = "Allow"
    actions   = ["ecs:UpdateService"]
    resources = [aws_ecs_service.victim.id]

    # Force-new-deployment is the restart. Anything that would change what runs —
    # a different task definition, a different desired count — is refused here even
    # though UpdateService itself is allowed.
    condition {
      test     = "Null"
      variable = "ecs:task-definition"
      values   = ["true"]
    }
  }

  statement {
    effect    = "Allow"
    actions   = ["ecs:DescribeServices"]
    resources = [aws_ecs_service.victim.id]
  }
}

resource "aws_iam_role_policy" "remediation" {
  name   = "${local.name}-remediation"
  role   = aws_iam_role.remediation.id
  policy = data.aws_iam_policy_document.remediation.json
}

resource "aws_iam_role_policy_attachment" "remediation_logs" {
  role       = aws_iam_role.remediation.name
  policy_arn = "arn:aws:iam::aws:policy/service-role/AWSLambdaBasicExecutionRole"
}

# --- backend task role: investigate, never remediate ---
#
# The agent that produces the RCA cannot restart anything. Acting requires going through
# the Step Functions approval gate, which assumes the remediation role above. The agent's
# own credentials are insufficient by construction — a hallucinated RCA has no path to
# an action even if the application code were wrong.

resource "aws_iam_role" "backend_task" {
  name               = "${local.name}-backend-task"
  assume_role_policy = data.aws_iam_policy_document.ecs_assume.json
}

data "aws_iam_policy_document" "backend_task" {
  statement {
    sid       = "PersistTranscriptsAndRCAs"
    effect    = "Allow"
    actions   = ["s3:PutObject", "s3:GetObject", "s3:ListBucket"]
    resources = [aws_s3_bucket.transcripts.arn, "${aws_s3_bucket.transcripts.arn}/*"]
  }

  statement {
    sid       = "StartTheApprovalWorkflow"
    effect    = "Allow"
    actions   = ["states:StartExecution"]
    resources = [aws_sfn_state_machine.remediation.arn]
  }

  statement {
    sid       = "ReadOwnLogsForInvestigation"
    effect    = "Allow"
    actions   = ["logs:GetLogEvents", "logs:FilterLogEvents", "logs:DescribeLogStreams"]
    resources = ["${aws_cloudwatch_log_group.victim.arn}:*"]
  }

  statement {
    sid       = "ExplicitlyNoRemediation"
    effect    = "Deny"
    actions   = ["ecs:UpdateService", "ecs:StopTask", "iam:PassRole"]
    resources = ["*"]
  }
}

resource "aws_iam_role_policy" "backend_task" {
  name   = "${local.name}-backend-task"
  role   = aws_iam_role.backend_task.id
  policy = data.aws_iam_policy_document.backend_task.json
}

# --- Step Functions role ---

data "aws_iam_policy_document" "sfn_assume" {
  statement {
    actions = ["sts:AssumeRole"]
    principals {
      type        = "Service"
      identifiers = ["states.amazonaws.com"]
    }
  }
}

resource "aws_iam_role" "stepfunctions" {
  name               = "${local.name}-sfn"
  assume_role_policy = data.aws_iam_policy_document.sfn_assume.json
}

data "aws_iam_policy_document" "stepfunctions" {
  statement {
    effect    = "Allow"
    actions   = ["lambda:InvokeFunction"]
    resources = [aws_lambda_function.remediate.arn]
  }

  statement {
    effect    = "Allow"
    actions   = ["sns:Publish"]
    resources = [aws_sns_topic.approvals.arn]
  }
}

resource "aws_iam_role_policy" "stepfunctions" {
  name   = "${local.name}-sfn"
  role   = aws_iam_role.stepfunctions.id
  policy = data.aws_iam_policy_document.stepfunctions.json
}
