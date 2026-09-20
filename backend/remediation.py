import json
import subprocess
import sys
import time
from datetime import datetime

import httpx

from atlas_sdk import AtlasClient, Decision, AtlasError
from database import SessionLocal
from models import Incident

VICTIM_CONTAINER = "victim-app"
HEALTH_URL = "http://localhost:8000/health"
VERIFY_WAIT_SECONDS = 8
VERIFY_ATTEMPTS = 3
VERIFY_RETRY_INTERVAL = 3

atlas = AtlasClient("https://atlas-production-c457.up.railway.app")

ATLAS_PRINCIPAL = "spiffe://ai-sre.local/system/approval-gate"
ATLAS_DELEGATE = "spiffe://ai-sre.local/agent/remediation-executor"


class IncidentNotPendingApproval(Exception):
    pass


def _restart_container(container_name: str) -> dict:
    try:
        result = subprocess.run(
            ["docker", "restart", container_name],
            capture_output=True,
            text=True,
            timeout=30,
        )
    except FileNotFoundError:
        return {"success": False, "error": "docker command not found on this machine"}
    except subprocess.TimeoutExpired:
        return {"success": False, "error": "docker restart timed out after 30s"}

    if result.returncode != 0:
        return {"success": False, "error": result.stderr.strip()}

    return {"success": True}


def _gated_restart(incident_id: int) -> dict:
    """Fail-closed by construction: every exit that isn't an explicit ACCEPT
    followed by a real restart attempt lands on 'failed'. There is no path
    that proceeds to docker restart without a verified capability."""
    try:
        grant = atlas.issue(
            principal=ATLAS_PRINCIPAL, delegate=ATLAS_DELEGATE,
            scope=[f"remediate:restart:{incident_id}"], ttl_seconds=120,
        )
    except AtlasError as e:
        return {"success": False, "error": f"capability issuance failed: {e}"}

    try:
        result = atlas.verify(grant.record)
    except AtlasError as e:
        return {"success": False, "error": f"capability verification failed: {e}"}

    if result.decision != Decision.ACCEPT:
        try:
            atlas.revoke(grant.instance)
        except AtlasError:
            pass
        return {"success": False, "error": f"capability rejected: {result.decision}"}

    restart_result = _restart_container(VICTIM_CONTAINER)

    try:
        atlas.revoke(grant.instance)
    except AtlasError as e:
        # Non-fatal: even if revoke never lands, the grant's 120s TTL plus Atlas's
        # ~30s clock-skew grace on expiry bounds the exposure at ~150s worst case.
        print(f"[incident {incident_id}] revoke failed (non-fatal, expires within ~150s worst case): {e}")

    return restart_result


def _check_health() -> bool:
    try:
        response = httpx.get(HEALTH_URL, timeout=3)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


def approve_and_remediate(incident_id: int) -> dict:
    """Deliberately a plain (non-async) function: FastAPI's BackgroundTasks offloads
    sync callables to a thread pool automatically, so this ~15-20s blocking sequence
    (restart + wait + retry loop) never ties up the event loop that's serving the
    dashboard's polling requests at the same time."""
    db = SessionLocal()

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        db.close()
        raise ValueError(f"no incident with id {incident_id}")

    if incident.status != "pending_approval":
        status = incident.status
        db.close()
        raise IncidentNotPendingApproval(
            f"incident {incident_id} is not pending approval (status: {status})"
        )

    incident.status = "executing"
    db.commit()
    print(f"[incident {incident_id}] status -> executing")

    restart_result = _gated_restart(incident_id)

    if not restart_result["success"]:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        incident.status = "failed"
        db.commit()
        db.close()
        print(f"[incident {incident_id}] restart failed: {restart_result['error']}")
        return {
            "status": "failed",
            "reason": f"restart failed: {restart_result['error']}",
        }

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    incident.status = "verifying"
    db.commit()
    print(f"[incident {incident_id}] status -> verifying")

    time.sleep(VERIFY_WAIT_SECONDS)

    healthy = False
    for attempt in range(1, VERIFY_ATTEMPTS + 1):
        if _check_health():
            healthy = True
            break
        print(
            f"[incident {incident_id}] verify attempt {attempt}/{VERIFY_ATTEMPTS}: "
            "still unhealthy"
        )
        time.sleep(VERIFY_RETRY_INTERVAL)

    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if healthy:
        incident.status = "resolved"
        incident.resolved_at = datetime.utcnow()
        db.commit()
        db.close()
        print(f"[incident {incident_id}] status -> resolved (verified healthy)")
        return {"status": "resolved"}

    incident.status = "failed"
    db.commit()
    db.close()
    print(
        f"[incident {incident_id}] status -> failed "
        "(still unhealthy after restart + verification window)"
    )
    return {
        "status": "failed",
        "reason": "still unhealthy after restart + verification window",
    }


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("usage: python remediation.py <incident_id>")
        sys.exit(1)

    try:
        result = approve_and_remediate(int(sys.argv[1]))
    except IncidentNotPendingApproval as exc:
        print(f"blocked: {exc}")
        sys.exit(1)

    print(json.dumps(result, indent=2))
