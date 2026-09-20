# AI-SRE AWS infrastructure

Terraform for running AI-SRE on AWS. Written against the council's verdict: **the depth
goes into one hard edge — identity-scoped authorization around the remediation action —
not into service count.** ECS Fargate, not EKS; no multi-account, no service mesh.

## The one architectural idea

The remediation action is authorized twice, by two independent systems that must agree:

1. **Atlas** (application layer) issues a one-shot, 120-second capability scoped to
   `remediate:restart:{incident_id}`, verifies it, and revokes it after use. Fail-closed.
2. **AWS IAM** (infrastructure layer) gives the remediation task a role that can call
   exactly one action — `ecs:UpdateService` on one specific service ARN — and nothing
   else, enforced by a permission boundary.

Neither trusts the other. If the agent is compromised or hallucinates, IAM still bounds
the blast radius to restarting one service; if IAM is misconfigured, Atlas still refuses
to mint a capability. That redundancy is the point, and it is what makes this more than
an SAA-level VPC diagram.

## Layout

| File | Contains |
|---|---|
| `main.tf` | Provider, locals, shared tags |
| `network.tf` | VPC, two AZs, public/private subnets, NAT, endpoints |
| `data.tf` | RDS Postgres, S3 transcript bucket, Secrets Manager |
| `ecs.tf` | Cluster, task definitions and services for victim-app / backend |
| `iam.tf` | **The interesting file.** Per-task roles, permission boundary, scoped remediation policy |
| `stepfunctions.tf` | The approval gate as an explicit state machine |
| `observability.tf` | Log groups, alarms, budget alarm |
| `variables.tf` / `outputs.tf` | Inputs and outputs |

## Cost

Roughly **$50–150/month** if left running. NAT Gateway (~$32), RDS db.t4g.micro (~$13),
ALB (~$16) are the floor; Fargate scales with task count. `budget_monthly_usd` sets a
budget alarm, defaulting to $50.

**To tear down:** `terraform destroy`. Nothing here is retained-on-delete except the S3
transcript bucket (deliberate — transcripts are the evaluation corpus).

## Apply

```bash
cd infra
terraform init
terraform plan -out=tf.plan     # review before applying
terraform apply tf.plan
```

Requires working credentials (`aws sts get-caller-identity` must succeed) and
`nim_api_key` supplied via `TF_VAR_nim_api_key` — never committed.
