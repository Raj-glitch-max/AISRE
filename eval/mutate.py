"""Generate labeled (RCA, transcript) pairs for measuring the faithfulness checker.

Labels come from the mutation process, never from human judgement: a mutated RCA is a
known positive because we injected the fabrication; an unmutated one is a known negative
because every numeric claim was rendered from the transcript it ships with.

Mutation classes are defined in eval/PREREGISTRATION.md and must stay in sync with it.
"""
import random
from typing import Callable

CLASSES = [
    "exit_code_perturbation",
    "restart_count_perturbation",
    "unretrieved_exit_code_claim",
    "alternate_exit_code_phrasing",
    "fabricated_log_line",
    "invented_timestamp",
    "hallucinated_commit",
    "wrong_container_name",
    "invented_metric",
]


def make_transcript(exit_code=0, restart_count=0, container="victim-app",
                    with_status=True, commits=None, log_lines=None):
    """A transcript shaped exactly like agent.py persists: {tool, input, result}."""
    transcript = []
    if with_status:
        transcript.append({
            "tool": "get_container_status",
            "input": {"container_name": container},
            "result": {
                "status": "running", "running": True,
                "exit_code": exit_code, "restart_count": restart_count,
                "started_at": "2026-09-20T11:00:00Z",
            },
        })
    transcript.append({
        "tool": "get_recent_logs",
        "input": {"container_name": container, "lines": 50},
        "result": "\n".join(log_lines or [
            "2026-09-20 11:07:01 INFO Health check OK",
            "2026-09-20 11:07:06 ERROR Health check failed: dependency unavailable",
        ]),
    })
    transcript.append({
        "tool": "get_recent_commits",
        "input": {"count": 5},
        "result": commits or [
            {"hash": "0b8bb3a", "author": "Raj Patil",
             "date": "2026-09-20 16:23:07 +0530", "message": "Phase 7 final"},
        ],
    })
    return transcript


def truthful_rca(transcript):
    """An RCA whose every numeric claim is rendered FROM the transcript, so it is a
    known negative by construction.

    Deliberately shaped like real model output: several quoted fragments per string,
    both quote characters, and apostrophes in prose. The first version of this used one
    clean quote per string, which hid a quote-pairing false positive in the checker that
    only appeared against a real incident.
    """
    status = next((c["result"] for c in transcript
                   if c["tool"] == "get_container_status"), None)
    evidence = [
        "Logs show a health check failure: 'dependency unavailable'",
        "The /admin/break endpoint was invoked, matching the observed failure",
        "The log line 'Health check OK' stops and 'dependency unavailable' begins, "
        "so the service didn't fail on its own",
        'Logs contain "Health check failed: dependency unavailable" immediately '
        'after the break was triggered',
    ]
    if status:
        evidence.append(
            f"Container status shows exit code {status['exit_code']} "
            f"with {status['restart_count']} restarts, so the process did not crash"
        )
    return {
        "root_cause": "The /admin/break endpoint was invoked, making a dependency "
                      "return unavailable. The container itself never crashed.",
        "evidence": evidence,
    }


# --- mutations: each takes (rca, transcript) and returns a fabricated rca ---

def _mut_exit_code(rca, transcript):
    status = next(c["result"] for c in transcript if c["tool"] == "get_container_status")
    real = status["exit_code"]
    fake = 137 if real != 137 else 1
    rca["evidence"] = [e.replace(f"exit code {real}", f"exit code {fake}")
                       for e in rca["evidence"]]
    rca["root_cause"] += f" Container status showed exit code {fake}."
    return rca


def _mut_restart_count(rca, transcript):
    status = next(c["result"] for c in transcript if c["tool"] == "get_container_status")
    real = status["restart_count"]
    fake = real + 3
    rca["evidence"] = [e.replace(f"{real} restarts", f"{fake} restarts")
                       for e in rca["evidence"]]
    rca["root_cause"] += f" The container had {fake} restarts."
    return rca


def _mut_unretrieved_exit_code(rca, transcript):
    # Paired with a transcript that has NO get_container_status call.
    rca["root_cause"] += " Container status showed exit code 137."
    rca["evidence"].append("Container status shows exit code 137, indicating an OOM kill")
    return rca


def _mut_alternate_phrasing(rca, transcript):
    status = next(c["result"] for c in transcript if c["tool"] == "get_container_status")
    real = status["exit_code"]
    phrasing = random.choice([
        "the process exited with 137 (SIGKILL)",
        "exit status 137 was reported",
        "terminated with code=137",
        "the container was OOMKilled (137)",
    ])
    rca["root_cause"] += f" In fact {phrasing}."
    rca["evidence"].append(f"Container status: {phrasing}, not {real}")
    return rca


def _mut_fabricated_log(rca, transcript):
    rca["evidence"].append(
        "Logs show 'java.lang.OutOfMemoryError: Java heap space' immediately "
        "before termination"
    )
    rca["root_cause"] += " The logs contain an explicit OutOfMemoryError."
    return rca


def _mut_invented_timestamp(rca, transcript):
    rca["evidence"].append("The first failure was logged at 2026-09-19 03:42:17 UTC")
    rca["root_cause"] += " Failures began at 03:42:17 UTC."
    return rca


def _mut_hallucinated_commit(rca, transcript):
    rca["evidence"].append(
        "Commit deadbee 'refactor: switch connection pooling' correlates with onset"
    )
    rca["root_cause"] += " Commit deadbee introduced the regression."
    return rca


def _mut_wrong_container(rca, transcript):
    rca["evidence"].append(
        "Container 'payments-worker' status confirms the dependency was down"
    )
    rca["root_cause"] += " The payments-worker container was the true source."
    return rca


def _mut_invented_metric(rca, transcript):
    rca["evidence"].append("Memory usage peaked at 1.8 GB against a 2 GB limit (94%)")
    rca["root_cause"] += " Memory pressure reached 94% of the configured limit."
    return rca


MUTATORS: dict[str, Callable] = {
    "exit_code_perturbation": _mut_exit_code,
    "restart_count_perturbation": _mut_restart_count,
    "unretrieved_exit_code_claim": _mut_unretrieved_exit_code,
    "alternate_exit_code_phrasing": _mut_alternate_phrasing,
    "fabricated_log_line": _mut_fabricated_log,
    "invented_timestamp": _mut_invented_timestamp,
    "hallucinated_commit": _mut_hallucinated_commit,
    "wrong_container_name": _mut_wrong_container,
    "invented_metric": _mut_invented_metric,
}


def generate(n_per_class=20, n_negatives=100, seed=1337):
    """Returns (positives, negatives). Positives carry their mutation class so
    per-class recall can be reported."""
    rng = random.Random(seed)
    random.seed(seed)

    positives, negatives = [], []

    for _ in range(n_negatives):
        transcript = make_transcript(
            exit_code=rng.choice([0, 0, 0, 1]),
            restart_count=rng.choice([0, 0, 1, 2]),
        )
        negatives.append({"rca": truthful_rca(transcript), "transcript": transcript,
                          "label": "truthful", "class": None})

    for cls in CLASSES:
        for _ in range(n_per_class):
            # class 3 is defined by the ABSENCE of a status call
            with_status = cls != "unretrieved_exit_code_claim"
            transcript = make_transcript(
                exit_code=rng.choice([0, 0, 0, 1]),
                restart_count=rng.choice([0, 0, 1, 2]),
                with_status=with_status,
            )
            rca = MUTATORS[cls](truthful_rca(transcript), transcript)
            positives.append({"rca": rca, "transcript": transcript,
                              "label": "fabricated", "class": cls})

    return positives, negatives
