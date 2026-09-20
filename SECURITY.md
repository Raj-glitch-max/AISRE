# Security

## Reporting

Open a [security advisory](https://github.com/Raj-glitch-max/AISRE/security/advisories/new)
rather than a public issue. This is a personal research project with no SLA, but reports
are read.

## Threat model

The interesting question here is not "can the server be hacked" — it is **"what is the
worst thing a confidently wrong language model can cause?"**

The answer this project is built around: **a wrong explanation, never a wrong action.**

| Control | What it stops | Verified how |
|---|---|---|
| Fixed action space | The model's `recommended_action` text is never executed — only displayed. The action space has one member | By construction; no code path passes model output to a shell |
| Human approval | No remediation without an explicit approve | Guard enforced in the API route *and* in `approve_and_remediate` |
| Atlas capability | One-shot, 120s TTL, scoped `remediate:restart:{id}`, revoked after use, fail-closed | 6 scenarios incl. Atlas unreachable, explicit reject, and `INCONCLUSIVE` |
| IAM permission boundary (AWS) | `ecs:UpdateService` on exactly one ARN, cannot be widened by a later policy attach, task-definition changes refused | Terraform in [`infra/iam.tf`](infra/iam.tf) |
| Agent role deny (AWS) | The role that *writes* the RCA is explicitly denied `ecs:UpdateService` | Same |

**The faithfulness checker is not a security control.** It has 0% recall on held-out
fabrication classes ([`eval/RESULTS.md`](eval/RESULTS.md)) and is deliberately not wired
into the remediation path. Treating a measurement tool as a safety gate would create a
weak second mechanism where a strong first one already exists.

## Known limitations

- The victim service is a toy with an unauthenticated `/admin/break` endpoint. In the AWS
  deployment it has **no public route** and lives on private DNS inside the VPC — do not
  expose it.
- The faithfulness checker verifies token presence, not semantic entailment. False
  assertions composed entirely of true values pass through it. This is structural.
- Prompt injection via log content is **not** mitigated. An attacker who can write to the
  investigated service's logs can influence the RCA text. They cannot influence the
  action, which is the property that makes this survivable.

## Credential handling

Never commit credentials. `.env`, `rootkey.csv`, `*.tfstate` and credential CSVs are
gitignored.

**If you are following this repo as a template, do not create AWS root access keys.**
They cannot be scoped, cannot be restricted by policy, and a leak costs you the account
including billing. Create an IAM user, or use SSO. Terraform state contains the generated
database password and your model API key in plaintext — treat `*.tfstate` as a secret and
use a remote backend with encryption for anything real.
