# Resume Facts — AISRE (AI Incident Detection & Remediation)

*Generated: 2026-10-29 | Commit: $(git rev-parse HEAD) | Branch: final-polish*
*All numbers below are verified against code via `scripts/reproduce.py` and `CLAIMS_LEDGER.md`*

---

## Verified Technical Facts

### Architecture & Core Loop
- **5-second health poller** opens incidents automatically when victim-app `/health` returns non-200 (backend/poller.py:14)
- **LLM tool-calling agent** with 3 tools: `get_container_status`, `get_recent_logs`, `get_recent_commits` (backend/agent.py:219-285)
- **Schema-enforced RCA output**: root_cause (string), confidence (0.0-1.0), evidence (string[]), recommended_action (string), risk (low|medium|high) — validated before persistence (backend/agent.py:398-431)
- **Tool transcript persisted BEFORE any action** — incident.status = "pending_approval" stored in DB with full tool calls + results (backend/agent.py:656-658)
- **Model output never executed** — only fixed action is `docker restart victim-app` (or ECS forceNewDeployment / API restart), gated by human approval token (backend/remediation.py:192-215, backend/main.py:81-124)

### Fabrication Detection (Faithfulness Checker)
| Version | Designed Classes (n=180) | Held-Out Classes (n=120) | FPR |
|---------|-------------------------|-------------------------|-----|
| v0 (2 regexes) | 33.3% recall (60/180) | Not tested | 0% |
| v1 (evidence grounding) | 100% recall (180/180) | 0% recall (0/120) | 0% |

- **6 held-out mutation classes**: semantic_inversion, invented_causal_link, entity_hallucination, numeric_drift, tool_output_mismatch, omitted_evidence (eval/heldout.py:1-85)
- **Pre-registration committed before evaluation** — git history: PREREGISTRATION.md (3debe2c) → results (f3a2cbc) (verified in CLAIMS_LEDGER.md #8)
- **Checker v0 frozen at tag** `faithfulness-checker-v0` (commit 0b8bb3a)

### Authorization & Security (AWS Deployment)
- **Atlas capability-based auth**: one-shot capability with 120s TTL, revoked after use (backend/remediation.py:294, 323)
- **IAM permission boundary** on backend task role (infra/iam.tf:82-94)
- **Explicit deny statements** on backend role: `iam:*`, `ec2:*`, `rds:Delete*`, `secretsmanager:DeleteSecret`, `s3:DeleteObject` (infra/iam.tf:203-208)
- **Remediation role scoped to ONE ECS service** — explicit deny on `ecs:UpdateService`, `ecs:StopTask`, `iam:PassRole` except target service ARN (infra/iam.tf:203-208)
- **Step Functions approval gate** with human callback endpoint (infra/stepfunctions.tf, backend/main.py:127-155)

### Infrastructure (Terraform)
- **63 Terraform resource blocks** (not 59 as previously claimed) — counted via `grep -r "^resource " infra/ --include="*.tf" | wc -l`
- Resources include: ECS Fargate service + task definition, ALB, RDS PostgreSQL, Step Functions state machine, S3 buckets, Secrets Manager secrets, IAM roles + policies, CloudWatch log groups/alarms, VPC/subnets/SGs
- Reproducible via `scripts/reproduce.py` — re-derives all headline numbers from code

### Demo / Public Deployment (Render Free Tier)
- **Two services**: aisre-backend (Docker, serves API + dashboard at /dashboard) + aisre-victim (Docker)
- **Health checks** on both via `/health` endpoints
- **ENABLE_DEMO flag** gates `/demo/trigger-incident` endpoint (backend/main.py:158-171)
- **Default APPROVAL_TOKEN** for demo: "demo-approval-token" (backend/main.py:22) — override in production
- **Mock investigation fallback** when NIM_KEY not set (backend/agent.py:77-124, 458-481)

### Testing & Reproducibility
- **12 defect categories (D1-D12)** encoded as strict-xfail tests (tests/test_defects.py)
- **Reproduce harness** (`scripts/reproduce.py`) exits non-zero on drift — validates all claims in CI
- **CI pipeline**: reproduce → terraform validate → secret scan (`.github/workflows/ci.yml`)

---

## Skills Evidence (STAR Format)

### 1. LLM Agent Architecture (Tool-Calling Loop)
- **Situation**: Needed automated incident investigation without hallucinated actions
- **Task**: Design agent that gathers evidence via tools, outputs schema-validated JSON, never executes model text
- **Action**: Built 3-tool loop (container status, logs, git commits) with minimum 2 tool calls required, schema validation (_validate_rca), transcript persisted before any human action
- **Result**: Agent produces structured RCA with 100% schema compliance; model text shown to human, only fixed restart action ever executed

### 2. Fabrication Detection Research
- **Situation**: LLMs hallucinate in RCA — needed measurable detection
- **Task**: Build and evaluate faithfulness checkers with pre-registered predictions
- **Action**: v0 (2 regexes) → 33.3% recall; v1 (evidence grounding with 5 extractors: exit_code, restart_count, log_quote, commit_sha, timestamp) → 100% on designed, 0% on 6 held-out classes (semantic inversion, etc.)
- **Result**: Honest reporting — v1 fails on held-out (0% recall), pre-registration committed before eval, reproduce script verifies

### 3. Capability-Based Authorization (Atlas)
- **Situation**: Remediation must be gated — no standing privileges
- **Task**: Implement one-shot capability with TTL, revocation, offline fallback
- **Action**: Atlas integration: issue capability (remediate:restart:victim-app, 120s TTL) → verify → execute → revoke; offline JWT decode fallback if Atlas unreachable
- **Result**: Remediation fails closed without valid capability; exposure bounded to ~150s worst case (120s TTL + 30s clock skew)

### 4. Least-Privilege AWS Infrastructure
- **Situation**: Deploy remediation automation to AWS without over-permissioned roles
- **Task**: Terraform infra with permission boundary + explicit denies
- **Action**: Backend role: permission boundary + deny iam:*/ec2:*/rds:Delete*/etc. Remediation role: allow ONLY ecs:UpdateService on ONE service ARN, deny everything else
- **Result**: Blast radius = one ECS service; backend cannot modify infra, cannot escalate

### 5. End-to-End Reproducibility
- **Situation**: Claims in README must stay in sync with code
- **Task**: Build harness that re-derives every number from source
- **Action**: `scripts/reproduce.py` runs mutation eval, counts Terraform resources, checks git tags, validates schema — exits non-zero on any drift
- **Result**: CI catches README drift automatically; 5/5 headline claims verified

### 6. Public Demo Hardening
- **Situation**: Deploy to Render free tier for portfolio demo
- **Task**: Make safe for public internet — no real restarts, rate limits, auth
- **Action**: ENABLE_DEMO flag, mock investigation fallback, API-based simulated restart (/admin/fix), APPROVAL_TOKEN default, cooldown on trigger endpoints
- **Result**: Visitor can click "BREAK VICTIM-APP" → see investigation → approve → see resolution, no real containers touched

---

## Resume Bullets (Plain, Verifiable)

- **Built an LLM agent that investigates service incidents** — 3 tools (container status, logs, git history), requires ≥2 tool calls, outputs schema-validated JSON (root_cause, confidence, evidence[], recommended_action, risk), full transcript persisted before human review
- **Designed and evaluated two fabrication checkers** — v0: 2 regexes, 33.3% recall on 180 designed mutations; v1: evidence grounding with 5 extractors, 100% recall on designed, 0% on 6 held-out classes (semantic inversion, invented causal link, etc.); pre-registered predictions committed before evaluation
- **Implemented capability-based authorization for remediation** — Atlas SDK: one-shot capability (remediate:restart:<service>, 120s TTL), verified + revoked after use, offline JWT fallback, fail-closed design
- **Authored least-privilege AWS infrastructure (Terraform, 63 resources)** — ECS Fargate, ALB, RDS, Step Functions, S3, Secrets Manager; backend role: permission boundary + explicit denies (iam:*, ec2:*, rds:Delete*); remediation role: scoped to ONE ECS service with deny on all other ecs:UpdateService calls
- **Built reproducibility harness** — `scripts/reproduce.py` re-derives every README number from code (mutation recall, resource counts, tag existence); CI fails on drift
- **Hardened public demo for Render free tier** — ENABLE_DEMO flag gates trigger endpoint, mock investigation when no NIM_KEY, API-simulated restart via victim-app /admin/fix, token auth on approval, cooldown on demo endpoints

---

## Interview Questions (With Verifiable Answers)

### Q: "Walk me through the incident lifecycle in your system."
**A**: 5s poller detects failed /health → creates incident (status=open) → agent runs investigation loop (min 2 tool calls: container status, logs, commits) → outputs schema-validated RCA JSON → persisted with status=pending_approval + full tool transcript → human clicks Approve with token → remediation: issue Atlas capability (120s TTL) → verify → docker restart (or ECS forceNewDeployment) → revoke capability → wait 8s → 3 health checks → status=resolved or failed. Every step auditable in DB.

### Q: "How do you prevent the LLM from taking destructive actions?"
**A**: Three layers: (1) Model only outputs JSON — recommended_action is stored as text, never executed. (2) Only action in codebase is `_restart_container("victim-app")` — hardcoded name, no parameters from model. (3) That restart is gated by: human approval token + Atlas capability (remediate:restart:victim-app, 120s TTL, revoked after use). Without valid capability, `_gated_restart` returns failed.

### Q: "Your v1 checker gets 100% on designed mutations but 0% on held-out. What does that mean?"
**A**: v1 uses evidence grounding (5 extractors: exit_code, restart_count, log_quote, commit_sha, timestamp). Designed mutations break specific evidence patterns v1 knows. Held-out mutations are semantically different — e.g., semantic_inversion: every token is real (exit code 0, "healthy") but assertion says "crashed" — v1 sees valid evidence, misses the inverted claim. This is expected: evidence grounding detects fabrication *relative to observed evidence*, not semantic truth. Honest about the gap.

### Q: "How does the Atlas capability system work?"
**A**: Remediation calls `atlas.issue(principal, delegate, scope=["remediate:restart:victim-app"], ttl_seconds=120)` → gets signed JWT record → `atlas.verify(record)` → if ACCEPT, executes restart → `atlas.revoke(instance)`. If Atlas unreachable, offline JWT decode checks exp + scope. Capability is one-shot (revoked), TTL bounds exposure to ~150s worst case. Backend task role has explicit deny on ecs:UpdateService — cannot restart without capability.

### Q: "What's the blast radius if the backend is compromised?"
**A**: Backend task role: permission boundary + explicit deny on iam:*, ec2:*, rds:Delete*, secretsmanager:DeleteSecret, s3:DeleteObject. Cannot modify infra, cannot escalate privileges. Remediation role (separate): allow ONLY ecs:UpdateService on ONE service ARN, explicit deny on all other ecs:UpdateService/StopTask/iam:PassRole. Compromised backend = read incidents, trigger investigations. Compromised remediation = restart one service.

### Q: "How do you know your README claims match the code?"
**A**: `scripts/reproduce.py` re-derives every headline number: runs mutation eval (v0/v1 recall/FPR), counts Terraform resources (63, not 59), checks git tag exists (faithfulness-checker-v0), validates pre-registration commit order. CI runs this on every PR — exits non-zero on drift. CLAIMS_LEDGER.md maps each claim to file:line and verification command.

### Q: "What would you change about the held-out 0% result?"
**A**: Evidence grounding alone can't catch semantic inversion (real evidence, opposite claim). Would need: (1) cross-reference with ground truth (container actually running?), (2) consistency checker across tool calls (container status says running, logs show crash?), (3) larger eval set to measure precision/recall tradeoff. Current v1 is a baseline — honest about limitations.

---

## Files to Reference
- `backend/agent.py` — investigation loop, tool validation, mock fallback
- `backend/remediation.py` — gated restart, Atlas capability, health verification
- `backend/main.py` — FastAPI endpoints, approval token, demo trigger
- `backend/tools.py` — 3 tools with input validation (container_name, lines, count, repo_path)
- `backend/faithfulness_eval.py` — v1 checker with 5 evidence extractors
- `eval/mutate.py` — 9 designed mutation classes
- `eval/heldout.py` — 6 held-out mutation classes
- `eval/run_faithfulness_eval.py` — recall/FPR measurement
- `scripts/reproduce.py` — re-derives all claims
- `infra/iam.tf` — permission boundary, explicit denies, scoped remediation role
- `infra/stepfunctions.tf` — approval gate state machine
- `tests/test_defects.py` — D1-D12 defect tests (xfail)
- `docs/CLAIMS_LEDGER.md` — claim → verification mapping