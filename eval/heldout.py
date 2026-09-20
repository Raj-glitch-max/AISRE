"""Held-out fabrication classes the v1 checker was NOT designed against.

v1 scored 100% on eval/mutate.py — but the same author wrote both the mutator and the
checker, so that number measures fit, not generalization. It is the same structural error
as KLRB's leaked label: a result derived from data the detector had already seen.

These classes are deliberately chosen to probe the failure modes v1's own docstring
admits: it verifies token *presence*, not semantic entailment, and it extracts a fixed
set of claim shapes. Three of these six carry no fabricated token at all — every value
they cite is genuinely in the evidence, used to assert something false.
"""
from mutate import make_transcript, truthful_rca

HELDOUT_CLASSES = [
    "unshaped_numeric_claim",
    "semantic_inversion",
    "invented_causal_link",
    "paraphrased_log_content",
    "fabricated_network_detail",
    "uncalled_tool_attribution",
]


def _unshaped_numeric(rca, transcript):
    # Numbers in shapes the extractor does not look for: counts, latencies, replicas.
    rca["evidence"].append(
        "There were 3 consecutive probe failures with latency rising to 450ms "
        "across 5 replicas"
    )
    rca["root_cause"] += " Three consecutive probes failed across five replicas."
    return rca


def _semantic_inversion(rca, transcript):
    # Every token is real. The assertion is the opposite of what the evidence shows.
    rca["evidence"].append(
        "Container status shows running=False, confirming the process is stopped"
    )
    rca["root_cause"] += " The container is no longer running."
    return rca


def _invented_causal_link(rca, transcript):
    # Both facts are genuinely in evidence; the causal relation between them is invented.
    rca["evidence"].append(
        "The health check failure was caused by the most recent commit, which "
        "changed dependency handling"
    )
    rca["root_cause"] += " The recent commit directly caused the dependency failure."
    return rca


def _paraphrased_log(rca, transcript):
    # Fabricated log content, unquoted — evades the quoted-span check entirely.
    rca["evidence"].append(
        "The logs report an out of memory condition shortly before the process "
        "was terminated by the kernel"
    )
    rca["root_cause"] += " Logs indicate an out-of-memory termination."
    return rca


def _fabricated_network(rca, transcript):
    rca["evidence"].append(
        "Connection attempts to 10.0.4.17 on port 5432 were refused"
    )
    rca["root_cause"] += " The database at 10.0.4.17:5432 refused connections."
    return rca


def _uncalled_tool(rca, transcript):
    # Attributes evidence to a data source that was never queried at all.
    rca["evidence"].append(
        "Prometheus metrics confirm the error rate crossed the alerting threshold "
        "before the incident opened"
    )
    rca["root_cause"] += " Metrics confirmed the threshold breach."
    return rca


HELDOUT_MUTATORS = {
    "unshaped_numeric_claim": _unshaped_numeric,
    "semantic_inversion": _semantic_inversion,
    "invented_causal_link": _invented_causal_link,
    "paraphrased_log_content": _paraphrased_log,
    "fabricated_network_detail": _fabricated_network,
    "uncalled_tool_attribution": _uncalled_tool,
}


def generate_heldout(n_per_class=20, seed=4242):
    import random
    rng = random.Random(seed)
    positives = []
    for cls in HELDOUT_CLASSES:
        for _ in range(n_per_class):
            transcript = make_transcript(
                exit_code=rng.choice([0, 0, 1]),
                restart_count=rng.choice([0, 0, 1]),
            )
            rca = HELDOUT_MUTATORS[cls](truthful_rca(transcript), transcript)
            positives.append({"rca": rca, "transcript": transcript,
                              "label": "fabricated", "class": cls})
    return positives
