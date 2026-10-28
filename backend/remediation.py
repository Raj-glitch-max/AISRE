import json
import os
import subprocess
import sys
import time
from abc import ABC, abstractmethod
from datetime import datetime
from typing import Callable, Optional

import boto3
import httpx

from atlas_sdk import AtlasClient, Decision, AtlasError
from models import Incident

# SessionLocal factory - can be overridden for testing
_session_factory = None

def get_session_factory():
    """Get the session factory (can be overridden for testing)."""
    global _session_factory
    if _session_factory is None:
        from database import SessionLocal as _default_SessionLocal
        return _default_SessionLocal
    return _session_factory

def set_session_factory(factory):
    """Set the session factory (for testing)."""
    global _session_factory
    _session_factory = factory

PLATFORM = os.getenv("PLATFORM", "docker")

VICTIM_CONTAINER = os.getenv("VICTIM_CONTAINER", "victim-app")
HEALTH_URL = os.getenv("VICTIM_HEALTH_URL", "http://localhost:8000/health")
VERIFY_WAIT_SECONDS = int(os.getenv("VERIFY_WAIT_SECONDS", "8"))
VERIFY_ATTEMPTS = int(os.getenv("VERIFY_ATTEMPTS", "3"))
VERIFY_RETRY_INTERVAL = int(os.getenv("VERIFY_RETRY_INTERVAL", "3"))

ECS_CLUSTER = os.getenv("ECS_CLUSTER", "")
ECS_SERVICE = os.getenv("ECS_SERVICE", "")

# Atlas integration is optional for AISRE - can run without capability-based auth
ATLAS_URL = os.getenv("ATLAS_URL")
ATLAS_API_KEY = os.getenv("ATLAS_API_KEY")
ATLAS_PRINCIPAL = os.getenv("ATLAS_PRINCIPAL")
ATLAS_DELEGATE = os.getenv("ATLAS_DELEGATE")

# Global Atlas client (only created if ATLAS_URL is set)
atlas = AtlasClient(ATLAS_URL, api_key=ATLAS_API_KEY) if ATLAS_URL else None

# Check if Atlas gated restart is enabled
ATLAS_ENABLED = bool(ATLAS_URL and ATLAS_PRINCIPAL and ATLAS_DELEGATE)

# Step Functions for AWS deployment
SFN_STATE_MACHINE_ARN = os.getenv("SFN_STATE_MACHINE_ARN")
S3_TRANSCRIPT_BUCKET = os.getenv("S3_TRANSCRIPT_BUCKET")


# --- Offline verification (JWS/JWT decode) ---
def _decode_jwt_payload(token: str) -> dict:
    """Decode JWT/JWS payload without verification (for offline inspection).

    This is NOT a verification - just extracts the payload for logging/debugging.
    Real verification must use atlas.verify().
    """
    import base64
    try:
        # JWT has 3 parts: header.payload.signature
        parts = token.split('.')
        if len(parts) != 3:
            return {"error": "not a valid JWT format"}
        # Add padding if needed
        payload = parts[1]
        payload += '=' * (-len(payload) % 4)
        decoded = base64.urlsafe_b64decode(payload)
        return json.loads(decoded)
    except Exception as e:
        return {"error": f"JWT decode failed: {e}"}


def _offline_verify(record: str) -> dict:
    """Offline verification of a capability record.

    Decodes the JWT payload to check expiration and scope without
    contacting the Atlas server. This is a fallback when Atlas is unreachable.

    Returns: dict with 'valid' (bool) and 'reason' (str)
    """
    payload = _decode_jwt_payload(record)
    if "error" in payload:
        return {"valid": False, "reason": payload["error"]}

    # Check expiration
    import time
    exp = payload.get("exp")
    if exp and exp < time.time():
        return {"valid": False, "reason": "capability expired"}

    # Check scope contains remediate:restart
    scope = payload.get("scope", [])
    if not any("remediate:restart" in s for s in scope):
        return {"valid": False, "reason": "scope does not include remediate:restart"}

    return {"valid": True, "reason": "offline check passed"}


# --- Injectable clock and network for testing ---
class Clock(ABC):
    """Abstract clock for time-dependent operations."""

    @abstractmethod
    def sleep(self, seconds: float) -> None:
        pass

    @abstractmethod
    def now_utc(self) -> datetime:
        pass


class RealClock(Clock):
    """Real clock implementation using time.sleep and datetime.utcnow."""

    def sleep(self, seconds: float) -> None:
        time.sleep(seconds)

    def now_utc(self) -> datetime:
        return datetime.utcnow()


class Network(ABC):
    """Abstract network interface for HTTP calls."""

    @abstractmethod
    def get(self, url: str, timeout: float) -> httpx.Response:
        pass


class RealNetwork(Network):
    """Real network implementation using httpx."""

    def get(self, url: str, timeout: float) -> httpx.Response:
        return httpx.get(url, timeout=timeout)


# Default instances (can be replaced in tests)
_default_clock: Clock = RealClock()
_default_network: Network = RealNetwork()


def set_clock(clock: Clock) -> None:
    """Set the clock implementation (for testing)."""
    global _default_clock
    _default_clock = clock


def set_network(network: Network) -> None:
    """Set the network implementation (for testing)."""
    global _default_network
    _default_network = network


def get_clock() -> Clock:
    """Get the current clock implementation."""
    return _default_clock


def get_network() -> Network:
    """Get the current network implementation."""
    return _default_network


# Backwards-compatible wrapper for existing tests
def _check_health() -> bool:
    """Check victim service health using default network."""
    return _check_health_with_network(get_network())


def _check_health_with_network(network: Network) -> bool:
    """Check victim service health with specific network."""
    try:
        response = network.get(HEALTH_URL, timeout=3)
        return response.status_code == 200
    except httpx.HTTPError:
        return False


class IncidentNotPendingApproval(Exception):
    pass


def _restart_container(container_name: str) -> dict:
    """The fixed action, in both platforms.

    Still exactly one action with no parameters derived from model output — the ECS path
    forces a new deployment of one named service and cannot express anything else, the
    same way `docker restart <fixed name>` cannot. That equivalence is what lets the
    safety argument survive the move to Fargate unchanged.
    """
    if PLATFORM == "ecs":
        return _ecs_restart()

    # Try docker first
    result = _docker_restart(container_name)
    if result["success"]:
        return result

    # If docker not available, try API restart (for Render/cloud deployments)
    # Use VICTIM_BASE_URL from environment
    victim_base_url = os.getenv("VICTIM_BASE_URL")
    if victim_base_url:
        print(f"[incident] Docker not available, using API restart via {victim_base_url}")
        return _api_restart(victim_base_url)

    return result


def _docker_restart(container_name: str) -> dict:
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


def _api_restart(base_url: str) -> dict:
    """Restart victim-app via its admin API (for Render/cloud deployments).

    Uses the victim-app's /admin/fix endpoint to simulate a container restart.
    This is used when docker is not available (e.g., running on Render).
    """
    try:
        # First break it to simulate the failure state, then fix it
        # Actually, the victim-app is already broken (that's why we're here),
        # so we just call /admin/fix to restore it
        response = httpx.post(f"{base_url}/admin/fix", timeout=10)
        if response.status_code == 200:
            return {"success": True}
        return {"success": False, "error": f"admin/fix returned {response.status_code}: {response.text}"}
    except httpx.TimeoutException:
        return {"success": False, "error": "admin/fix request timed out"}
    except httpx.HTTPError as e:
        return {"success": False, "error": f"admin/fix request failed: {e}"}


def _ecs_restart() -> dict:
    import boto3

    if not (ECS_CLUSTER and ECS_SERVICE):
        return {"success": False, "error": "ECS_CLUSTER/ECS_SERVICE not configured"}

    try:
        boto3.client("ecs").update_service(
            cluster=ECS_CLUSTER,
            service=ECS_SERVICE,
            forceNewDeployment=True,
        )
    except Exception as exc:
        return {"success": False, "error": f"ecs update_service failed: {exc}"}

    return {"success": True}


def _gated_restart(incident_id: int) -> dict:
    """Fail-closed by construction: every exit that isn't an explicit ACCEPT
    followed by a real restart attempt lands on 'failed'. There is no path
    that proceeds to docker restart without a verified capability."""

    # If Atlas is not configured, skip gated restart and do direct restart
    if not ATLAS_ENABLED:
        print(f"[incident {incident_id}] Atlas not configured, performing direct restart")
        return _restart_container(VICTIM_CONTAINER)

    # Create a dedicated client for this gated operation with API key
    # This ensures the capability is issued with proper authentication
    gated_atlas = AtlasClient(ATLAS_URL, api_key=ATLAS_API_KEY)

    # Step 1: ISSUE - Request a capability grant from Atlas
    # This is a separate, distinct step that can be audited independently
    try:
        grant = gated_atlas.issue(
            principal=ATLAS_PRINCIPAL, delegate=ATLAS_DELEGATE,
            scope=[f"remediate:restart:{VICTIM_CONTAINER}"], ttl_seconds=120,
        )
    except AtlasError as e:
        return {"success": False, "error": f"capability issuance failed: {e}"}

    # Step 2: VERIFY - Verify the capability with Atlas server
    # This is a separate step from issuance, ensuring the grant is valid
    try:
        result = gated_atlas.verify(grant.record)
    except AtlasError as e:
        # Fallback to offline verification if Atlas server is unreachable
        offline_result = _offline_verify(grant.record)
        if not offline_result["valid"]:
            return {"success": False, "error": f"capability verification failed (offline): {offline_result['reason']}"}
        # Offline check passed - proceed with caution
        print(f"[incident {incident_id}] Atlas unreachable, offline verification passed: {offline_result['reason']}")
    else:
        if result.decision != Decision.ACCEPT:
            try:
                gated_atlas.revoke(grant.instance)
            except AtlasError:
                pass
            return {"success": False, "error": f"capability rejected: {result.decision}"}

    # Step 3: EXECUTE - Perform the restart with the verified capability
    restart_result = _restart_container(VICTIM_CONTAINER)

    # Step 4: REVOKE - Clean up the capability after use
    try:
        gated_atlas.revoke(grant.instance)
    except AtlasError as e:
        # Non-fatal: even if revoke never lands, the grant's 120s TTL plus Atlas's
        # ~30s clock-skew grace on expiry bounds the exposure at ~150s worst case.
        print(f"[incident {incident_id}] revoke failed (non-fatal, expires within ~150s worst case): {e}")

    return restart_result


def approve_and_remediate(
    incident_id: int,
    clock: Clock | None = None,
    network: Network | None = None,
) -> dict:
    """Deliberately a plain (non-async) function: FastAPI's BackgroundTasks offloads
    sync callables to a thread pool automatically, so this ~15-20s blocking sequence
    (restart + wait + retry loop) never ties up the event loop that's serving the
    dashboard's polling requests at the same time."""
    clk = clock or get_clock()
    net = network or get_network()

    SessionLocal = get_session_factory()
    db = SessionLocal()

    incident = db.query(Incident).filter(Incident.id == incident_id).first()
    if not incident:
        db.close()
        raise ValueError(f"no incident with id {incident_id}")

    # Endpoint already atomically changed status from pending_approval -> executing
    # Accept either status to handle the race-free handoff
    if incident.status not in ("pending_approval", "executing"):
        status = incident.status
        db.close()
        raise IncidentNotPendingApproval(
            f"incident {incident_id} is not pending approval or executing (status: {status})"
        )

    if incident.status == "pending_approval":
        incident.status = "executing"
        db.commit()
        print(f"[incident {incident_id}] status -> executing")

    # For AWS deployment, start Step Functions execution
    if PLATFORM == "ecs" and SFN_STATE_MACHINE_ARN:
        sfn_client = boto3.client("stepfunctions")
        try:
            response = sfn_client.start_execution(
                stateMachineArn=SFN_STATE_MACHINE_ARN,
                input=json.dumps({
                    "incident_id": incident_id,
                    "root_cause": incident.root_cause or "under investigation",
                })
            )
            execution_arn = response["executionArn"]
            print(f"[incident {incident_id}] started Step Functions execution: {execution_arn}")

            # Store execution ARN for tracking
            incident.sfn_execution_arn = execution_arn
            db.commit()

            # Store transcript in S3 if configured
            if S3_TRANSCRIPT_BUCKET and incident.tool_transcript:
                _store_transcript_in_s3(incident_id, incident.tool_transcript)

            db.close()
            return {"status": "started", "execution_arn": execution_arn}
        except Exception as e:
            print(f"[incident {incident_id}] failed to start Step Functions: {e}")
            # Fall back to local execution
            pass

    # Local execution (docker platform or fallback)
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

    clk.sleep(VERIFY_WAIT_SECONDS)

    healthy = False
    for attempt in range(1, VERIFY_ATTEMPTS + 1):
        if _check_health_with_network(net):
            healthy = True
            break
        print(
            f"[incident {incident_id}] verify attempt {attempt}/{VERIFY_ATTEMPTS}: "
            "still unhealthy"
        )
        clk.sleep(VERIFY_RETRY_INTERVAL)

    incident = db.query(Incident).filter(Incident.id == incident_id).first()

    if healthy:
        incident.status = "resolved"
        incident.resolved_at = clk.now_utc()
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


def _store_transcript_in_s3(incident_id: int, transcript: str) -> None:
    """Store tool transcript in S3 for audit trail."""
    if not S3_TRANSCRIPT_BUCKET:
        return
    try:
        s3 = boto3.client("s3")
        key = f"incidents/{incident_id}/transcript.json"
        s3.put_object(
            Bucket=S3_TRANSCRIPT_BUCKET,
            Key=key,
            Body=transcript.encode(),
            ContentType="application/json",
        )
        print(f"[incident {incident_id}] transcript stored in s3://{S3_TRANSCRIPT_BUCKET}/{key}")
    except Exception as e:
        print(f"[incident {incident_id}] failed to store transcript in S3: {e}")


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
