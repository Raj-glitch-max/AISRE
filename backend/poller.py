import asyncio
import logging
from datetime import datetime

import httpx

from database import SessionLocal
from models import Incident

TARGET_URL = "http://localhost:8000/health"
POLL_INTERVAL_SECONDS = 5
RESOLVE_AFTER_SUCCESSES = 2

logger = logging.getLogger("poller")

active_incident_id = None


async def run_poller():
    global active_incident_id
    consecutive_successes = 0

    async with httpx.AsyncClient(timeout=5) as client:
        while True:
            try:
                response = await client.get(TARGET_URL)
                healthy = response.status_code == 200
            except httpx.HTTPError:
                healthy = False

            db = SessionLocal()
            try:
                if not healthy:
                    consecutive_successes = 0
                    if active_incident_id is None:
                        incident = Incident(status="open")
                        db.add(incident)
                        db.commit()
                        db.refresh(incident)
                        active_incident_id = incident.id
                        logger.error("Incident %s opened: victim-app unhealthy", incident.id)
                else:
                    consecutive_successes += 1
                    if active_incident_id is not None and consecutive_successes >= RESOLVE_AFTER_SUCCESSES:
                        incident = db.query(Incident).get(active_incident_id)
                        incident.status = "resolved"
                        incident.resolved_at = datetime.utcnow()
                        db.commit()
                        logger.info("Incident %s resolved", incident.id)
                        active_incident_id = None
                        consecutive_successes = 0
            finally:
                db.close()

            await asyncio.sleep(POLL_INTERVAL_SECONDS)
