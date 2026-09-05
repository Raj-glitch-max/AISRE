import asyncio
import json
import logging
import os

import httpx
from fastapi import BackgroundTasks, FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles

from database import Base, SessionLocal, engine
from models import Incident
from poller import run_poller
from remediation import approve_and_remediate

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")

Base.metadata.create_all(bind=engine)

app = FastAPI()


@app.on_event("startup")
async def start_poller():
    asyncio.create_task(run_poller())


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
def approve_incident(incident_id: int, background_tasks: BackgroundTasks):
    # Checked here, synchronously, before the task is scheduled — not only inside
    # approve_and_remediate(). BackgroundTasks runs after the response is already
    # sent, so a guard living only in there would return "started" to an invalid
    # request and surface the rejection nowhere but the server log.
    db = SessionLocal()
    try:
        incident = db.query(Incident).filter(Incident.id == incident_id).first()
        if not incident:
            raise HTTPException(status_code=404, detail="incident not found")
        if incident.status != "pending_approval":
            raise HTTPException(
                status_code=409,
                detail=f"incident is not pending approval (status: {incident.status})",
            )
    finally:
        db.close()

    background_tasks.add_task(approve_and_remediate, incident_id)
    return {"status": "approval received, remediation started"}


@app.post("/demo/trigger-incident")
def demo_trigger():
    # A non-technical visitor can't run curl against the loopback-only admin
    # endpoint directly (nor should they be able to — victim-app stays internal).
    # This proxies the one safe action: break it, let the auto-trigger + agent
    # take it from there.
    httpx.post("http://localhost:8000/admin/break", timeout=3)
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
