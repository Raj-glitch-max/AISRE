# Preregistration — faithfulness checker measurement

**Written and committed BEFORE the evaluation was run.** Verify with
`git log --diff-filter=A -- eval/PREREGISTRATION.md` and compare against the commit that
adds `eval/results/`.

Checker under test is frozen at tag `faithfulness-checker-v0`
(commit `0b8bb3a`, `backend/faithfulness_eval.py`, 79 lines, two regexes).

## Why this exists

The checker was written *after* seeing incident #3's fabrication and validated *against
that same incident*. That is n=1 fit to the sample — structurally the same error that
produced KLRB's retracted "Evidence Invariance" headline (a finding derived from data
already seen). Claiming it is a "faithfulness checker" is not supportable until its
recall and false-positive rate are measured against fabrications it was not built from.

## What is being measured

A binary classifier over (RCA, tool_transcript) pairs:

- **Positives** — RCAs containing at least one programmatically injected fabrication.
  A correct result is ≥1 flag raised.
- **Negatives** — RCAs whose every numeric claim is consistent with the transcript.
  A correct result is zero flags.

Labels come from the mutation process, not from human judgement. No RCA is hand-scored.

Metrics reported: **recall** (fabrications caught / fabrications injected), **false
positive rate** (truthful RCAs flagged / truthful RCAs), and **per-mutation-class recall**
(the "miss list").

## Mutation classes injected

| # | Class | Example | Predicted |
|---|---|---|---|
| 1 | Exit code perturbation | `exit code 0` → `exit code 137` | **caught** |
| 2 | Restart count perturbation | `0 restarts` → `3 restarts` | **caught** |
| 3 | Exit-code claim with no `get_container_status` call | asserts a code never retrieved | **caught** |
| 4 | Alternate exit-code phrasing | `exit status 137`, `exited with 137`, `code=137` | **missed** |
| 5 | Fabricated log line | quotes a log line absent from transcript | **missed** |
| 6 | Invented timestamp | cites a time not present in any tool output | **missed** |
| 7 | Hallucinated commit hash | cites a SHA absent from `get_recent_commits` | **missed** |
| 8 | Wrong container name | attributes evidence to a container never inspected | **missed** |
| 9 | Other invented metric | `memory usage 1.8 GB`, `CPU at 94%` | **missed** |

## Predictions (recorded before running)

1. **Overall recall: 20–40%.** Only classes 1–3 are within the regexes' reach; they are
   3 of 9 classes, so recall tracks class balance rather than detection skill.
2. **Per-class recall ≈ 100% for classes 1–3, ≈ 0% for classes 4–9.** The checker matches
   two fixed phrasings against two fields; nothing else is representable.
3. **False positive rate: 0%.** The checker only flags on a numeric mismatch against a
   retrieved value, so a truthful RCA should produce no flags. A non-zero FPR would be
   the genuinely surprising result and would indicate a bug, not a limitation.
4. **Class 4 (phrasing variants) is the most damaging miss** — the same fabricated fact
   as class 1, worded differently, is invisible. That is a detector keyed to surface form
   rather than to the claim.

## What would falsify the "it works" claim

Recall below ~40% means the checker cannot be described as a faithfulness checker. It
would be accurately described as: *detects numeric claims about container exit code and
restart count; blind to every other fabrication class.* If the measurement says that, the
README says that.

## Analysis constraints

- The checker is not modified until after the first measurement is recorded.
- Results are reported whatever they are, including a recall near zero.
- Any post-measurement improvement to the checker is measured on freshly generated
  mutations, and both numbers are published.
