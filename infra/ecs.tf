resource "aws_ecs_cluster" "main" {
  name = local.name

  setting {
    name  = "containerInsights"
    value = "enabled"
  }
}

resource "aws_ecr_repository" "backend" {
  name                 = "${local.name}/backend"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

resource "aws_ecr_repository" "victim" {
  name                 = "${local.name}/victim-app"
  image_tag_mutability = "MUTABLE"
  force_delete         = true

  image_scanning_configuration {
    scan_on_push = true
  }
}

# --- victim-app: the thing that breaks ---

resource "aws_ecs_task_definition" "victim" {
  family                   = "${local.name}-victim"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 256
  memory                   = 512
  execution_role_arn       = aws_iam_role.task_execution.arn

  # Deliberately no task role: victim-app has no business calling any AWS API.
  container_definitions = jsonencode([{
    name      = "victim-app"
    image     = var.victim_image != "" ? var.victim_image : "${aws_ecr_repository.victim.repository_url}:latest"
    essential = true

    portMappings = [{ containerPort = 8000, protocol = "tcp" }]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.victim.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "victim"
      }
    }
  }])
}

resource "aws_ecs_service" "victim" {
  name            = "${local.name}-victim"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.victim.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.victim.id]
  }

  service_registries {
    registry_arn = aws_service_discovery_service.victim.arn
  }

  # The remediation path issues force-new-deployment; without this, Terraform would
  # fight it on the next apply.
  lifecycle {
    ignore_changes = [desired_count]
  }
}

# --- backend: poller, agent, faithfulness checker, dashboard ---

resource "aws_ecs_task_definition" "backend" {
  family                   = "${local.name}-backend"
  requires_compatibilities = ["FARGATE"]
  network_mode             = "awsvpc"
  cpu                      = 512
  memory                   = 1024
  execution_role_arn       = aws_iam_role.task_execution.arn
  task_role_arn            = aws_iam_role.backend_task.arn

  container_definitions = jsonencode([{
    name      = "backend"
    image     = var.backend_image != "" ? var.backend_image : "${aws_ecr_repository.backend.repository_url}:latest"
    essential = true

    portMappings = [{ containerPort = 9000, protocol = "tcp" }]

    environment = [
      { name = "ATLAS_URL", value = var.atlas_url },
      { name = "VICTIM_HEALTH_URL", value = "http://victim.${aws_service_discovery_private_dns_namespace.main.name}:8000/health" },
      { name = "VICTIM_BASE_URL", value = "http://victim.${aws_service_discovery_private_dns_namespace.main.name}:8000" },
      { name = "PLATFORM", value = "ecs" },
      { name = "ECS_CLUSTER", value = aws_ecs_cluster.main.name },
      { name = "ECS_SERVICE", value = aws_ecs_service.victim.name },
      { name = "VICTIM_LOG_GROUP", value = aws_cloudwatch_log_group.victim.name },
      { name = "TRANSCRIPT_BUCKET", value = aws_s3_bucket.transcripts.id },
      { name = "REMEDIATION_STATE_MACHINE", value = aws_sfn_state_machine.remediation.arn },
      { name = "DB_HOST", value = aws_db_instance.main.address },
    ]

    secrets = [
      { name = "NIM_KEY", valueFrom = aws_secretsmanager_secret.nim_key.arn },
      { name = "DB_SECRET", valueFrom = aws_secretsmanager_secret.db.arn },
    ]

    logConfiguration = {
      logDriver = "awslogs"
      options = {
        "awslogs-group"         = aws_cloudwatch_log_group.backend.name
        "awslogs-region"        = var.region
        "awslogs-stream-prefix" = "backend"
      }
    }
  }])
}

resource "aws_ecs_service" "backend" {
  name            = "${local.name}-backend"
  cluster         = aws_ecs_cluster.main.id
  task_definition = aws_ecs_task_definition.backend.arn
  desired_count   = 1
  launch_type     = "FARGATE"

  network_configuration {
    subnets         = aws_subnet.private[*].id
    security_groups = [aws_security_group.backend.id]
  }

  load_balancer {
    target_group_arn = aws_lb_target_group.backend.arn
    container_name   = "backend"
    container_port   = 9000
  }

  depends_on = [aws_lb_listener.http]
}

# --- load balancer ---

resource "aws_lb" "main" {
  name               = "${local.name}-alb"
  internal           = false
  load_balancer_type = "application"
  security_groups    = [aws_security_group.alb.id]
  subnets            = aws_subnet.public[*].id
}

resource "aws_lb_target_group" "backend" {
  name        = "${local.name}-backend"
  port        = 9000
  protocol    = "HTTP"
  vpc_id      = aws_vpc.main.id
  target_type = "ip"

  health_check {
    path                = "/incidents"
    matcher             = "200"
    interval            = 30
    healthy_threshold   = 2
    unhealthy_threshold = 3
  }
}

resource "aws_lb_listener" "http" {
  load_balancer_arn = aws_lb.main.arn
  port              = 80
  protocol          = "HTTP"

  default_action {
    type             = "forward"
    target_group_arn = aws_lb_target_group.backend.arn
  }
}
