"""Check an RCA's specific factual claims against the evidence the agent actually saw.

v1. The v0 implementation (frozen at tag `faithfulness-checker-v0`) matched two fixed
regexes against two fields of get_container_status. Measured recall was 33.3%: perfect
on the three fabrication classes those regexes could represent, zero on the six they
could not — including the same fabricated fact merely reworded.

v1 inverts the approach. Rather than asking "does this known field match?", it asks
"is this asserted token traceable to anything the agent retrieved?" Every tool result in
the transcript is flattened into an evidence corpus, and each specific claim extracted
from the RCA must be groundable in it. That generalizes to claim types never enumerated
here, which is the property v0 lacked.

Known limits (measured, see eval/results/): this greps for claim shapes, so a fabrication
phrased in a shape not extracted here is still invisible, and it verifies token presence
rather than semantic entailment — a number present in evidence but describing something
else will pass.
"""
import sys
import json
import re

from database import SessionLocal
from models import Incident

# A number in exit-status context. Deliberately a context window rather than a list of
# phrasings: "exit code 137", "exit status 137", "exited with 137", "code=137" and
# "OOMKilled (137)" all land, without enumerating each one (that enumeration was exactly
# v0's failure mode, one level up).
_EXIT_CLAIM = re.compile(
    r"(?:exit|exited|status|code|sigkill|oomkill(?:ed)?|killed|terminated|signal)"
    r"[^.\n]{0,30}?\b(\d{1,3})\b",
    re.IGNORECASE,
)
_RESTART_CLAIM = re.compile(
    r"(?:\b(\d+)\s*restarts?\b|restart[_ ]count[^\d\n]{0,10}(\d+))",
    re.IGNORECASE,
)
# Backreference on the quote character is load-bearing: without it the regex pairs one
# span's closing quote with the next span's opening quote and "quotes" the prose between
# them. Real RCAs contain several quoted fragments, so that produced false positives on
# incident #7 that the synthetic corpus (one quote per string) never exercised.
_QUOTED = re.compile(
    r"(?:(?<=\s)|^)([\"'])([^\"'\n]{12,}?)\1(?=[\s.,;:)\]]|$)"
)
_COMMIT_HASH = re.compile(r"\b(?=[0-9a-f]*\d|[0-9a-f]{7,})([0-9a-f]{7,40})\b")
_TIMESTAMP = re.compile(r"\b(\d{4}-\d{2}-\d{2}[ T]\d{2}:\d{2}:\d{2}|\d{2}:\d{2}:\d{2})\b")
_NAMED_CONTAINER = re.compile(r"container\s+['\"]([^'\"\n]+)['\"]", re.IGNORECASE)
_PERCENT = re.compile(r"\b(\d+(?:\.\d+)?)\s*%")
_SIZE = re.compile(r"\b(\d+(?:\.\d+)?)\s*(?:GB|MB|KB|GiB|MiB|KiB)\b", re.IGNORECASE)


def extract_ground_truth(tool_transcript):
    """Structured values the transcript establishes directly."""
    tool_transcript = tool_transcript or []
    truth = {"exit_code": None, "restart_count": None, "status_called": False}
    for call in tool_transcript:
        result = call.get("result")
        if call.get("tool") == "get_container_status" and isinstance(result, dict):
            truth["status_called"] = True
            truth["exit_code"] = result.get("exit_code")
            truth["restart_count"] = result.get("restart_count")
    return truth


def _evidence_text(tool_transcript):
    """Everything the agent actually retrieved, flattened to searchable text."""
    parts = []
    for call in tool_transcript or []:
        result = call.get("result")
        parts.append(result if isinstance(result, str) else json.dumps(result))
        parts.append(json.dumps(call.get("input") or {}))
    return "\n".join(parts)


def _normalize(text):
    return re.sub(r"\s+", " ", text).strip().lower()


def check_faithfulness(rca: dict, tool_transcript: list) -> dict:
    truth = extract_ground_truth(tool_transcript)
    evidence = _evidence_text(tool_transcript)
    evidence_norm = _normalize(evidence)

    text = (rca.get("root_cause") or "") + " " + " ".join(rca.get("evidence") or [])

    seen, flagged, checked = set(), [], 0

    def flag(key, claim, reason):
        if key in seen:
            return
        seen.add(key)
        flagged.append({"claim": claim, "reason": reason})

    # --- exit status claims: compare against the retrieved value when there is one ---
    for m in _EXIT_CLAIM.finditer(text):
        claimed = int(m.group(1))
        checked += 1
        if not truth["status_called"]:
            flag(("exit", claimed), m.group(0).strip(),
                 "claims an exit status, but get_container_status was never called")
        elif truth["exit_code"] is not None and claimed != truth["exit_code"]:
            flag(("exit", claimed), m.group(0).strip(),
                 f"tool output actually showed exit_code={truth['exit_code']}")

    # --- restart counts ---
    for m in _RESTART_CLAIM.finditer(text):
        claimed = int(m.group(1) or m.group(2))
        checked += 1
        if not truth["status_called"]:
            flag(("restart", claimed), m.group(0).strip(),
                 "claims a restart count, but get_container_status was never called")
        elif truth["restart_count"] is not None and claimed != truth["restart_count"]:
            flag(("restart", claimed), m.group(0).strip(),
                 f"tool output actually showed restart_count={truth['restart_count']}")

    # --- quoted spans: a quoted log line must appear in what was retrieved ---
    for m in _QUOTED.finditer(text):
        quoted = m.group(2)
        checked += 1
        if _normalize(quoted) not in evidence_norm:
            flag(("quote", _normalize(quoted)), quoted,
                 "quoted as evidence, but this string appears nowhere in the tool output")

    # --- commit hashes ---
    for m in _COMMIT_HASH.finditer(text):
        sha = m.group(1)
        checked += 1
        if sha.lower() not in evidence_norm:
            flag(("commit", sha.lower()), sha,
                 "cites a commit that get_recent_commits never returned")

    # --- timestamps ---
    for m in _TIMESTAMP.finditer(text):
        ts = m.group(1)
        checked += 1
        if _normalize(ts) not in evidence_norm:
            flag(("time", _normalize(ts)), ts,
                 "cites a timestamp that appears nowhere in the tool output")

    # --- explicitly named containers ---
    for m in _NAMED_CONTAINER.finditer(text):
        name = m.group(1)
        checked += 1
        if _normalize(name) not in evidence_norm:
            flag(("container", _normalize(name)), name,
                 "attributes evidence to a container that was never inspected")

    # --- invented metrics (percentages, byte sizes) ---
    for pattern, kind in ((_PERCENT, "percentage"), (_SIZE, "size")):
        for m in pattern.finditer(text):
            value = m.group(1)
            checked += 1
            if value not in evidence_norm:
                flag((kind, value), m.group(0).strip(),
                     f"cites a {kind} with no basis in the tool output")

    return {"flagged": flagged, "checked_claims": checked}


def run(incident_id: int):
    db = SessionLocal()
    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    db.close()
    if not incident:
        print(f"no incident {incident_id}")
        return

    if not incident.tool_transcript:
        print(f"incident {incident_id}: no transcript recorded (investigated before this feature existed)")
        return

    rca = {
        "root_cause": incident.root_cause,
        "evidence": json.loads(incident.evidence) if incident.evidence else [],
    }
    transcript = json.loads(incident.tool_transcript)
    result = check_faithfulness(rca, transcript)

    print(f"incident {incident_id}: checked {result['checked_claims']} specific claim(s)")
    if not result["flagged"]:
        print("  no unsupported claims found")
    for f in result["flagged"]:
        print(f"  UNSUPPORTED: \"{f['claim']}\" — {f['reason']}")


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python faithfulness_eval.py <incident_id>")
        sys.exit(1)
    run(int(sys.argv[1]))
