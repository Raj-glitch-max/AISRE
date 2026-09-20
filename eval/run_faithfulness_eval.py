"""Measure the frozen faithfulness checker against labeled mutations.

Reports recall, false-positive rate, and per-class recall (the miss list).
Writes eval/results/faithfulness_v0.json and prints a summary table.
"""
import json
import os
import subprocess
import sys

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "backend"))
sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))

from faithfulness_eval import check_faithfulness  # noqa: E402
from mutate import CLASSES, generate  # noqa: E402

RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")


def _checker_commit():
    try:
        return subprocess.run(
            ["git", "rev-parse", "--short", "faithfulness-checker-v0"],
            capture_output=True, text=True, cwd=os.path.dirname(os.path.abspath(__file__)),
        ).stdout.strip() or "unknown"
    except Exception:
        return "unknown"


def main(label="v0"):
    positives, negatives = generate()

    per_class = {c: {"total": 0, "caught": 0} for c in CLASSES}
    caught_total = 0

    for case in positives:
        result = check_faithfulness(case["rca"], case["transcript"])
        flagged = len(result["flagged"]) > 0
        per_class[case["class"]]["total"] += 1
        if flagged:
            per_class[case["class"]]["caught"] += 1
            caught_total += 1

    false_positives = 0
    for case in negatives:
        result = check_faithfulness(case["rca"], case["transcript"])
        if len(result["flagged"]) > 0:
            false_positives += 1

    recall = caught_total / len(positives) if positives else 0.0
    fpr = false_positives / len(negatives) if negatives else 0.0

    out = {
        "checker_frozen_at": f"faithfulness-checker-v0 ({_checker_commit()})",
        "label": label,
        "n_positives": len(positives),
        "n_negatives": len(negatives),
        "recall": round(recall, 4),
        "false_positive_rate": round(fpr, 4),
        "per_class_recall": {
            c: {
                "caught": v["caught"],
                "total": v["total"],
                "recall": round(v["caught"] / v["total"], 4) if v["total"] else None,
            }
            for c, v in per_class.items()
        },
    }

    os.makedirs(RESULTS_DIR, exist_ok=True)
    path = os.path.join(RESULTS_DIR, f"faithfulness_{label}.json")
    with open(path, "w") as f:
        json.dump(out, f, indent=2)

    print(f"checker frozen at : {out['checker_frozen_at']}")
    print(f"positives         : {out['n_positives']}")
    print(f"negatives         : {out['n_negatives']}")
    print()
    print(f"RECALL            : {recall:.1%}  ({caught_total}/{len(positives)} fabrications caught)")
    print(f"FALSE POSITIVE RATE: {fpr:.1%}  ({false_positives}/{len(negatives)} truthful RCAs wrongly flagged)")
    print()
    print("per-class recall (the miss list):")
    for c in CLASSES:
        v = out["per_class_recall"][c]
        bar = "CAUGHT " if v["recall"] and v["recall"] > 0.5 else "BLIND  "
        print(f"  {bar} {v['recall']:.0%}  {c}  ({v['caught']}/{v['total']})")
    print()
    print(f"written to {path}")
    return out


if __name__ == "__main__":
    main(sys.argv[1] if len(sys.argv) > 1 else "v0")
