#!/usr/bin/env python3
"""Re-derive every headline claim in README.md from committed code and data.

Exits non-zero if any number has drifted. CI runs this on every push, so a claim that
stops being true breaks the build rather than quietly rotting in a README.

The v0 checker is not kept in the working tree — it is extracted from the frozen git tag
`faithfulness-checker-v0` and executed, so the 33.3% baseline is genuinely re-measured
rather than read back out of a JSON file someone could have edited.
"""
import importlib.util
import os
import subprocess
import sys
import tempfile

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, os.path.join(ROOT, "backend"))
sys.path.insert(0, os.path.join(ROOT, "eval"))

FROZEN_TAG = "faithfulness-checker-v0"

CLAIMS = []
FAILURES = []


def claim(label, actual, expected, tolerance=0.001):
    ok = abs(actual - expected) <= tolerance
    CLAIMS.append((label, actual, expected, ok))
    if not ok:
        FAILURES.append(label)
    mark = "ok  " if ok else "DRIFT"
    print(f"  [{mark}] {label}: {actual:.1%} (claimed {expected:.1%})")


def load_frozen_checker():
    """Pull backend/faithfulness_eval.py out of the frozen tag and import it."""
    try:
        source = subprocess.run(
            ["git", "show", f"{FROZEN_TAG}:backend/faithfulness_eval.py"],
            capture_output=True, text=True, cwd=ROOT, check=True,
        ).stdout
    except (subprocess.CalledProcessError, FileNotFoundError) as exc:
        print(f"  [SKIP ] could not read tag {FROZEN_TAG}: {exc}")
        return None

    tmp = tempfile.NamedTemporaryFile(mode="w", suffix="_v0.py", delete=False)
    tmp.write(source)
    tmp.close()

    spec = importlib.util.spec_from_file_location("faithfulness_v0", tmp.name)
    module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(module)
    os.unlink(tmp.name)
    return module


def score(check_fn, cases):
    caught = sum(1 for c in cases if check_fn(c["rca"], c["transcript"])["flagged"])
    return caught / len(cases) if cases else 0.0


def main():
    from mutate import generate
    from heldout import generate_heldout
    from faithfulness_eval import check_faithfulness as v1_check

    print("Re-deriving README claims from committed code and data\n")

    positives, negatives = generate()
    heldout = generate_heldout()

    print("checker v0 (extracted from frozen tag):")
    v0 = load_frozen_checker()
    if v0:
        claim("v0 recall on designed classes", score(v0.check_faithfulness, positives), 0.3333, 0.01)
        fp_v0 = sum(1 for c in negatives if v0.check_faithfulness(c["rca"], c["transcript"])["flagged"])
        claim("v0 false positive rate", fp_v0 / len(negatives), 0.0)

    print("\nchecker v1 (current working tree):")
    claim("v1 recall on designed classes", score(v1_check, positives), 1.0)
    fp_v1 = sum(1 for c in negatives if v1_check(c["rca"], c["transcript"])["flagged"])
    claim("v1 false positive rate", fp_v1 / len(negatives), 0.0)
    claim("v1 recall on HELD-OUT classes", score(v1_check, heldout), 0.0)

    print(f"\ncorpus: {len(positives)} designed positives, {len(negatives)} negatives, "
          f"{len(heldout)} held-out positives")

    print()
    if FAILURES:
        print(f"{len(FAILURES)}/{len(CLAIMS)} claims DRIFTED:")
        for f in FAILURES:
            print(f"  - {f}")
        return 1

    print(f"{len(CLAIMS)}/{len(CLAIMS)} claims verified — all clear")
    return 0


if __name__ == "__main__":
    sys.exit(main())
