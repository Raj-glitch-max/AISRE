import sys
import json
import re

from database import SessionLocal
from models import Incident

_EXIT_CODE_RE = re.compile(r"exit code\s*(\d+)", re.IGNORECASE)
_RESTART_COUNT_RE = re.compile(r"(\d+)\s*restarts?\b", re.IGNORECASE)


def extract_ground_truth(tool_transcript):
    tool_transcript = tool_transcript or []
    truth = {"exit_code": None, "restart_count": None}
    for call in tool_transcript:
        result = call.get("result")
        if call.get("tool") == "get_container_status" and isinstance(result, dict):
            truth["exit_code"] = result.get("exit_code")
            truth["restart_count"] = result.get("restart_count")
    return truth


def check_faithfulness(rca: dict, tool_transcript: list) -> dict:
    truth = extract_ground_truth(tool_transcript)
    text = (rca.get("root_cause") or "") + " " + " ".join(rca.get("evidence") or [])
    seen, flagged, checked = set(), [], 0

    for pattern, key, label in [(_EXIT_CODE_RE, "exit_code", "exit_code"),
                                  (_RESTART_COUNT_RE, "restart_count", "restart_count")]:
        for m in pattern.finditer(text):
            checked += 1
            claimed = int(m.group(1))
            dedupe_key = (key, claimed)
            if dedupe_key in seen:
                continue
            actual = truth[key]
            if actual is None:
                seen.add(dedupe_key)
                flagged.append({"claim": m.group(0),
                                 "reason": f"claims a {label}, but get_container_status was never called or returned none"})
            elif claimed != actual:
                seen.add(dedupe_key)
                flagged.append({"claim": m.group(0),
                                 "reason": f"tool output actually showed {label}={actual}"})

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
