## What changed, and why

## Did any published number move?

- [ ] No numbers changed
- [ ] Yes — and I updated `README.md`, `eval/RESULTS.md` and the claimed values in
      `scripts/reproduce.py` **in this same commit**

If a number moved, say which and in which direction — including if it got worse. A recall
that dropped is a finding worth publishing, not something to tune away.

## Checks

- [ ] `make reproduce` exits 0
- [ ] `make check` passes
- [ ] No credentials in the diff
- [ ] If I touched the checker or corpus, I froze before measuring and predicted before
      running (see [CONTRIBUTING.md](../CONTRIBUTING.md))
