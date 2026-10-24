import asyncio
import json
import logging
import os
from datetime import datetime

import boto3
import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException, Header
from fastapi.staticfiles import StaticFiles

from database import Base, SessionLocal, engine
from models import Incident
from poller import run_poller
from remediation import approve_and_remediate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

VICTIM_BASE_URL = os.getenv("VICTIM_BASE_URL", "http://localhost:8000")
# Approval token for authentication (required for /approve endpoint)
APPROVAL_TOKEN = os.getenv("APPROVAL_TOKEN")
# Step Functions for AWS deployment
SFN_STATE_MACHINE_ARN = os.getenv("SFN_STATE_MACHINE_ARN")

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.on_event("startup")
async def start_poller():
    asyncio.create_task(run_poller())


def verify_approval_token(authorization: str | None = Header(None)) -> None:
    """Verify the approval token from Authorization header."""
    if not APPROVAL_TOKEN:
        raise HTTPException(
            status_code=500,
            detail="APPROVAL_TOKEN not configured on server"
        )
    if not authorization:
        raise HTTPException(
            status_code=401,
            detail="Authorization header required"
        )
    # Support "Bearer <token>" or just "<token>"
    token = authorization.replace("Bearer ", "").strip()
    if token != APPROVAL_TOKEN:
        raise HTTPException(
            status_code=401,
            detail="Invalid approval token"
        )


@app.get("/incidents")
def list_incidents():
    db = SessionLocal()
    try:
        incidents = db.query(Incident).order_by(Incident.id).all()
        return [
            {
                "id": incident.id,
                "status": incident.status,
                "service_name": incident.service_name,
                "opened_at": incident.opened_at.isoformat() if incident.opened_at else None,
                "resolved_at": incident.resolved_at.isoformat() if incident.resolved_at else None,
                "root_cause": incident.root_cause,
                "confidence": incident.confidence,
                "evidence": json.loads(incident.evidence) if incident.evidence else None,
                "recommended_action": incident.recommended_action,
                "risk": incident.risk,
            }
            for incident in incidents
        ]
    finally:
        db.close()


@app.post("/incidents/{incident_id}/approve")
def approve_incident(
    incident_id: int,
    background_tasks: BackgroundTasks,
    authorization: str | None = Header(None)
):
    # Verify authentication token
    verify_approval_token(authorization)

    # Checked here, synchronously, before the task is scheduled — not only inside
    # approve_and_remediate(). BackgroundTasks runs after the response is already
    # sent, so a guard living only in there would return "started" to an invalid
    # request and surface the rejection nowhere but the server log.
    db = SessionLocal()
    try:
        # Lock the row to prevent race conditions
        incident = db.query(Incident).filter(Incident.id == incident_id).with_for_update().first()
        if not incident:
            raise HTTPException(status_code=404, detail="incident not found")
        if incident.status != "pending_approval":
            raise HTTPException(
                status_code=409,
                detail=f"incident is not pending approval (status: {incident.status})",
            )

        # Record approval info (race prevention: check-then-act in same transaction)
        # Use a single transaction to prevent race conditions
        incident.status = "executing"
        incident.approved_by = authorization.replace("Bearer ", "").strip()[:100]
        incident.approved_at = datetime.utcnow()
        db.commit()

    except HTTPException:
        db.close()
        raise
    except Exception as e:
        db.rollback()
        db.close()
        raise HTTPException(status_code=500, detail=f"approval failed: {e}")
    else:
        db.close()

    background_tasks.add_task(approve_and_remediate, incident_id)
    return {"status": "approval received, remediation started"}


@app.post("/approval/callback")
def approval_callback(task_token: str, approve: bool = True):
    """Callback endpoint for human approval to resume Step Functions execution.

    This endpoint receives the task token from the SNS notification and
    either continues or fails the Step Functions execution based on the
    human's decision.
    """
    if not SFN_STATE_MACHINE_ARN:
        raise HTTPException(
            status_code=501,
            detail="Step Functions not configured"
        )

    sfn_client = boto3.client("stepfunctions")

    if approve:
        sfn_client.send_task_success(
            taskToken=task_token,
            output=json.dumps({"approved": True})
        )
        return {"status": "approval sent, remediation continuing"}
    else:
        sfn_client.send_task_failure(
            taskToken=task_token,
            error="ApprovalDenied",
            cause="Human operator denied approval"
        )
        return {"status": "approval denied, remediation cancelled"}


@app.post("/demo/trigger-incident")
def demo_trigger():
    # A non-technical visitor can't run curl against the loopback-only admin
    # endpoint directly (nor should they be able to — victim-app stays internal).
    # This proxies the one safe action: break it, let the auto-trigger + agent
    # take it from there.
    # Require ENABLE_DEMO flag for safety
    if os.getenv("ENABLE_DEMO") != "true":
        raise HTTPException(
            status_code=403,
            detail="Demo endpoint disabled. Set ENABLE_DEMO=true to enable."
        )
    httpx.post(f"{VICTIM_BASE_URL}/admin/break", timeout=5)
    return {"status": "triggered"}


# Mounted last: a mount at "/" would otherwise shadow the API routes above.
app.mount(
    "/dashboard",
    StaticFiles(
        directory=os.path.join(os.path.dirname(os.path.abspath(__file__)), "static"),
        html=True,
    ),
    name="dashboard",
)
