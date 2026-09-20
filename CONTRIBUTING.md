# Contributing

This repository makes measured claims about how often an LLM agent fabricates evidence.
The contribution rules exist to keep those claims true.

## The one rule that matters

**Never measure a detector on data you wrote for it.**

This project has broken that rule three times, documented each time, and the whole point
of the repo is the resulting numbers. If your change touches the faithfulness checker or
the evaluation corpus, it has to survive that standard:

1. **Freeze before you measure.** Tag the checker, or note the commit. A number measured
   against code you tweaked afterwards is not a number.
2. **Predict before you run.** Add your prediction to
   [`eval/PREREGISTRATION.md`](eval/PREREGISTRATION.md) and *commit it* before generating
   results. Reviewers check the commit order.
3. **Labels come from the generator, never your judgement.** If you hand-score a single
   RCA, the result is an opinion.
4. **Report what you got.** A recall of 4% is a finding. Quietly re-tuning until the
   number looks good is the failure mode this repo exists to demonstrate.

## The best possible contribution

**Break the checker.** Write a fabrication class it cannot catch, add it to
[`eval/heldout.py`](eval/heldout.py), and open a PR titled with the recall you achieved.

Held-out classes that score 0% are not bugs — they are the most valuable thing you can
add, because they define the honest boundary of what the checker can claim. The current
boundary is known: it verifies *token presence*, not semantic entailment. Anything that
asserts something false using only true values walks straight through it.

## Before you open a PR

```bash
make reproduce   # must print "claims verified — all clear" and exit 0
make check       # every module imports
```

`make reproduce` re-derives every number in the README, including re-running the frozen v0
checker out of the git tag. CI runs it on every push. **If your change moves a published
number, update the README, [`eval/RESULTS.md`](eval/RESULTS.md) and the claimed values in
`scripts/reproduce.py` in the same commit** — never separately, or the repo spends time in
a state where it lies about itself.

## Commit messages

State what changed and why it was worth changing. If a number moved, say which number and
in which direction — including when it moved the wrong way. Look at `git log` for the
house style; failures are reported in the subject line, not buried in the body.

## What lives where

| Path | Rules |
|---|---|
| `backend/` | The running system. Keep the docker and ecs tool backends shape-identical — `eval/` reads `exit_code`/`restart_count` out of them, and a divergence breaks the evaluation with no error |
| `eval/` | Preregistration, generators, results. Results are append-only in spirit: don't overwrite a published number, add a new labelled run |
| `infra/` | Terraform. Never commit state — it contains the DB password and the NIM key in plaintext |
| `flow.md` | The engineering log. Failures go in with the same detail as successes |

## Security

Never commit credentials. `.env`, `rootkey.csv`, `*.tfstate` and credential CSVs are
gitignored; that is a safety net, not permission to be casual. See
[`SECURITY.md`](SECURITY.md).
