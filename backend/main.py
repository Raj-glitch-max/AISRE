import asyncio
import json
import logging

from fastapi import FastAPI

from database import Base, SessionLocal, engine
from models import Incident
from poller import run_poller

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
