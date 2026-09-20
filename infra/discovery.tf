# Private service discovery for victim-app.
#
# Why this exists: the backend's poller needs to reach victim-app, and the first version
# pointed it at the public ALB on a path the listener does not route. The poller dutifully
# read that 404 as "the service is down" and opened an incident — a false positive
# manufactured entirely by infrastructure, which is exactly the class of thing this
# project is supposed to be careful about.
#
# victim-app must also stay off the internet (it has an /admin/break endpoint), so the
# right answer is private DNS inside the VPC rather than another public listener rule.

resource "aws_service_discovery_private_dns_namespace" "main" {
  name        = "${local.name}.local"
  description = "Private DNS for intra-VPC service resolution"
  vpc         = aws_vpc.main.id
}

resource "aws_service_discovery_service" "victim" {
  name = "victim"

  dns_config {
    namespace_id = aws_service_discovery_private_dns_namespace.main.id

    dns_records {
      ttl  = 10
      type = "A"
    }

    routing_policy = "MULTIVALUE"
  }

  health_check_custom_config {
    failure_threshold = 1
  }
}
