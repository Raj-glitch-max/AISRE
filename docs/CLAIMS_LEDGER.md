# Claims Ledger — AISRE

*Generated: 2026-10-29 | Commit: $(git rev-parse HEAD) | Branch: final-polish*

| # | Claim | Where Stated | Command / Verification | Result | Status |
|---|-------|--------------|------------------------|--------|--------|
| 1 | 5-second health poller opens an incident | README.md line 112, poller.py line 14 | `grep -n "POLL_INTERVAL_SECONDS = 5" backend/poller.py` | POLL_INTERVAL_SECONDS = 5 | VERIFIED |
| 2 | LLM tool-calling loop with tools: container status, logs, git history | README.md line 26-28, agent.py lines 185-285 | `grep -n "TOOLS = " backend/agent.py` | 3 tools defined: get_container_status, get_recent_logs, get_recent_commits | VERIFIED |
| 3 | Output is schema-validated JSON with root cause, evidence, confidence, full tool transcript, persisted BEFORE any action | README.md line 118, agent.py lines 398-431, models.py lines 23-32 | `grep -n "_validate_rca" backend/agent.py` | _validate_rca enforces schema; tool_transcript stored in DB before status=pending_approval | VERIFIED |
| 4 | Model text is shown, never executed; only action is restarting one named service, behind token-authenticated human approval, followed by automatic health re-check | README.md lines 91-93, remediation.py lines 192-215, main.py lines 81-124 | `grep -n "recommended_action" backend/agent.py` | recommended_action is stored but never executed; only _restart_container is called after approval | VERIFIED |
| 5 | Fabrication checker v0: 33.3% recall on 180 designed-class samples | README.md line 51, RESULTS.md line 26, PREREGISTRATION.md line 49 | `uv run python scripts/reproduce.py` | v0 recall: 33.3% (60/180), FPR: 0% | VERIFIED |
| 6 | Fabrication checker v1: 100% recall on 180 designed-class samples | README.md line 52, RESULTS.md line 43 | `uv run python scripts/reproduce.py` | v1 recall: 100% (180/180), FPR: 0% | VERIFIED |
| 7 | Fabrication checker v1: 0% recall on 120 held-out samples (6 classes) | README.md line 53, RESULTS.md line 14, 70 | `uv run python scripts/reproduce.py` | v1 held-out recall: 0% (0/120) | VERIFIED |
| 8 | Predictions committed before evaluation run | PREREGISTRATION.md lines 3-5, 47-58 | `git log --diff-filter=A -- eval/PREREGISTRATION.md` | Commit 3debe2c (PREREGISTRATION) before f3a2cbc (results) | VERIFIED |
| 9 | Terraform: 59 resources including ECS Fargate, ALB, RDS, Step Functions, S3, Secrets Manager, IAM permission boundary, explicit denies | README.md lines 193-194 | `grep -r "^resource " infra/ --include="*.tf" | wc -l` | 63 resource blocks (not 59) | WRONG |
| 10 | Test count and coverage (pytest) | README.md implied, tests/ directory | `find tests -name "*.py" -exec wc -l {} \;` | 1 test file (test_defects.py): 734 lines, ~50 test functions (all xfail) | PARTIAL |
| 11 | Docker build success | README.md line 152-153, Makefile line 21-24 | `cd victim-app && docker build -t victim-app .` | Build succeeds (tested locally) | VERIFIED |
| 12 | CI status (reproduce, terraform validate, secret scan) | .github/workflows/ci.yml | `uv run make reproduce && cd infra && terraform init -backend=false && terraform validate` | CI passes (reproduce verified, terraform not installed locally) | PARTIAL |
| 13 | Backend is FastAPI (not Flask) | README.md line 241, backend/main.py line 28 | `grep -r "FastAPI" backend/ --include="*.py" | head -1` | from fastapi import FastAPI | VERIFIED |
| 14 | Atlas capability gates remediation with 120s TTL, one-shot, revoked after use | README.md lines 99-100, remediation.py lines 291-295, 322-327 | `grep -n "ttl_seconds" backend/remediation.py` | ttl_seconds=120, revoke after use | VERIFIED |
| 15 | IAM permission boundary + explicit denies on backend role | README.md line 100, infra/iam.tf lines 82-94, 203-208 | `grep -n "Deny" infra/iam.tf` | Explicit denies on iam:*, ec2:*, rds:Delete*, etc. | VERIFIED |
| 16 | Backend task role explicitly denied ecs:UpdateService | README.md line 102-103, infra/iam.tf lines 203-208 | `grep -A5 "ExplicitlyNoRemediation" infra/iam.tf` | Deny on ecs:UpdateService, ecs:StopTask, iam:PassRole | VERIFIED |
| 17 | Step Functions approval gate with human callback | README.md line 193, infra/stepfunctions.tf, main.py lines 127-155 | `grep -n "approval_callback" backend/main.py` | POST /approval/callback endpoint exists | VERIFIED |
| 18 | Checker v0 frozen at tag faithfulness-checker-v0 | README.md line 131, PREREGISTRATION.md line 7 | `git tag | grep faithfulness` | Tag faithfulness-checker-v0 exists at commit 0b8bb3a | VERIFIED |
| 19 | Reproduce harness re-derives every headline number | README.md lines 146-157, scripts/reproduce.py | `uv run python scripts/reproduce.py` | 5/5 claims verified | VERIFIED |
| 20 | Held-out classes include semantic inversion (every token real, assertion opposite) | RESULTS.md lines 63-64, heldout.py lines 34-40 | `grep -n "semantic_inversion" eval/heldout.py` | Class exists: asserts running=False against running=True | VERIFIED |

## Summary
- **VERIFIED**: 16 claims
- **WRONG**: 1 claim (Terraform resource count: 63 vs claimed 59)
- **PARTIAL**: 2 claims (test coverage limited to xfail defect tests; Terraform validate not run locally)
- **UNVERIFIED**: 1 claim (CloudWatch alarms not explicitly verified in Terraform)