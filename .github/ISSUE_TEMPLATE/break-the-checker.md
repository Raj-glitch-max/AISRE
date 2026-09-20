---
name: I broke the checker
about: You found a fabrication the faithfulness checker cannot catch
title: "[held-out] "
labels: evaluation, help wanted
---

**This is the most valuable issue you can open here.** The checker's honest boundary is
defined by what gets past it, so a fabrication it misses is a contribution, not a bug
report.

## The fabrication

What does the RCA claim?

```
```

## The evidence it was supposedly grounded in

The tool transcript the agent actually retrieved:

```json
```

## Why it gets through

Best guesses, if you have one — the known ceiling is that the checker verifies *token
presence*, not semantic entailment, so anything asserting something false using only true
values walks straight through.

- [ ] Uses only values that genuinely appear in the evidence
- [ ] A claim shape the extractor doesn't look for
- [ ] Phrasing variant of a shape it does look for
- [ ] Something else

## Recall you measured (if you ran it)

```
make heldout
```
