# Faithfulness checker — measured results

All numbers produced by `eval/run_faithfulness_eval.py` and `eval/heldout.py` against
labeled mutations. Labels come from the mutation process, never hand-scoring.
Predictions were committed in `eval/PREREGISTRATION.md` **before** the first run
(`git log --diff-filter=A -- eval/PREREGISTRATION.md`).

## Headline

| Checker | Corpus | Recall | FPR |
|---|---|---|---|
| v0 (frozen, 2 regexes) | 9 designed classes, n=180 | **33.3%** | 0.0% |
| v1 (evidence-grounding) | 9 designed classes, n=180 | **100%** | 0.0% |
| v1 (evidence-grounding) | 6 **held-out** classes, n=120 | **0.0%** | — |

**The third row is the result that matters.** The 100% is not a detection capability; it
is the signature of a detector evaluated on the same author's test set.

## v0 — the honest baseline

The original checker was 79 lines and two regexes (`exit code (\d+)`, `(\d+) restarts?`),
written *after* observing incident #3's fabrication and validated *against that same
incident*. n=1, fit to the sample.

Measured: **33.3% recall, 0% FPR.** Perfect on the three classes its regexes can
represent, zero on the six they cannot. Preregistered prediction was 20–40% recall, ~100%
on classes 1–3, ~0% on classes 4–9, and 0% FPR. All four predictions held.

The most damaging single miss: **the same fabricated fact, reworded, is invisible.**
`exit code 137` is caught; `exit status 137`, `exited with 137`, `code=137` and
`OOMKilled (137)` are not. That is a detector keyed to surface form, not to the claim.

Accurate description of v0: *detects numeric claims about container exit code and restart
count.* Not "a faithfulness checker."

## v1 — and why its 100% is worthless on its own

v1 replaced field-matching with evidence-grounding: flatten every tool result into an
evidence corpus, extract specific claim shapes from the RCA (exit-status numbers in a
context window, restart counts, quoted spans, commit hashes, timestamps, named
containers, percentages, byte sizes), and require each to be traceable to that corpus.

Measured: **100% recall, 0% FPR** across all nine classes.

**This number should not be trusted, and the reason is the entire point of this project.**
The same author wrote the mutation generator and the checker. v1 was designed knowing the
nine classes it would be scored on. A perfect score under those conditions measures fit,
not detection — structurally identical to KLRB's retracted "Evidence Invariance" headline,
which was produced by a benchmark grading a model on a label its own prompt had leaked.

Catching this in one's own detector is the third instance of the same failure mode in this
body of work: the agent fabricated an RCA (incident #3, reproduced live in #7), the
benchmark leaked its own label (KLRB), and now the detector overfit its own test set.

## The held-out test — the real number

Six fabrication classes were then written that v1 was **not** designed against, chosen to
probe the limitations v1's own docstring admits (token presence ≠ semantic entailment; a
fixed set of extracted claim shapes):

| Class | Recall | Why it evades |
|---|---|---|
| `unshaped_numeric_claim` | 0% | Counts/latencies/replicas are numeric shapes the extractor doesn't look for |
| `semantic_inversion` | 0% | **Every token is real.** `running=False` asserted against evidence showing running=True |
| `invented_causal_link` | 0% | **Every token is real.** Two true facts joined by an invented causal relation |
| `paraphrased_log_content` | 0% | Fabricated log content, unquoted — evades the quoted-span check |
| `fabricated_network_detail` | 0% | IPs and ports are not extracted claim shapes |
| `uncalled_tool_attribution` | 0% | Attributes findings to Prometheus, which was never queried |

**0 of 120 caught.**

Three of these six carry no fabricated token whatsoever. They are false *assertions*
composed entirely of true *values*. No amount of token-presence checking reaches them —
this is a structural ceiling of the approach, not a gap to be patched with more regexes.

## A third overfit, found in the measurement itself

The 0% false-positive rate was *also* initially an artifact. The synthetic truthful RCAs
used one clean quoted span per string. Real model output does not: incident #7's RCA
contains several quoted fragments per sentence, in both quote characters.

Run against that real incident, v1 raised **five false positives** — its quoted-span
regex paired one span's closing quote with the next span's opening quote and "quoted" the
prose between them. The synthetic negatives could never surface this, because they never
contained two quotes in one string.

Fixed by backreferencing the quote character, and the negatives were reshaped to look
like real output (multiple quoted fragments, both quote characters, apostrophes in
prose). Post-fix: 100% recall / 0% FPR on the designed corpus, 0% held-out — unchanged,
confirming the held-out gap is structural rather than a symptom of this bug.

The lesson generalizes past this project: **a self-authored negative corpus tends to be
too clean, and a 0% false-positive rate measured on it means less than it appears.** The
real incident was a better adversary than the generator was.

## What this licenses the project to claim

Supportable:
- The checker detects fabricated **values** in extracted claim shapes, with a measured 0%
  false-positive rate on truthful RCAs across both corpora.
- It caught incident #7's live fabrication automatically, unprompted (the model asserted
  "exit code 137 with 3 restarts" having never called `get_container_status`).
- Recall against fabrication classes it was designed for: 100%. Against classes it was
  not: **0%**.

Not supportable:
- "The system detects hallucinations." It detects a subset of value-level fabrications.
- Any recall number quoted without stating which corpus produced it.

## Why the safety argument survives anyway

The detector being weak does not make the system unsafe, because detection was never the
control. Remediation executes a **fixed, enumerated action**; the model's
`recommended_action` text is never executed. A fabricated RCA — caught or missed —
produces a wrong *explanation*, never a wrong *action*. Atlas gates that action behind a
one-shot capability independently of anything the checker concludes.

That separation is what makes a 0% held-out recall survivable: the checker is a *quality
measurement*, not a safety gate, and the safety property does not depend on it. The prior
design decision to keep these separate is what turns this result from a catastrophe into
a finding.

## Reproducing

```bash
cd eval
python run_faithfulness_eval.py v1      # designed classes
python -c "import heldout; ..."          # held-out classes (see git history)
```

Checker v0 is preserved at tag `faithfulness-checker-v0`.
