import asyncio
import logging
import threading
from datetime import datetime

import httpx

from agent import investigate
from database import SessionLocal
from models import Incident

TARGET_URL = "http://localhost:8000/health"
POLL_INTERVAL_SECONDS = 5
RESOLVE_AFTER_SUCCESSES = 2

logger = logging.getLogger("poller")

active_incident_id = None


def _investigate_safely(incident_id):
    """Runs in its own thread. If agent.investigate() throws — NVIDIA API down,
    rate-limited, whatever — the incident must not sit at 'investigating' forever
    with nothing watching it. On a laptop you'd notice and rerun by hand; on a
    server, nobody's watching."""
    try:
        investigate(incident_id)
    except Exception as e:
        logger.error("investigation failed for incident %s: %s", incident_id, e)
        try:
            db = SessionLocal()
            incident = db.query(Incident).filter(Incident.id == incident_id).first()
            if incident and incident.status == "investigating":
                incident.status = "failed"
                db.commit()
            db.close()
        except Exception:
            logger.error("could not even mark incident %s as failed", incident_id)


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
                        threading.Thread(
                            target=_investigate_safely,
                            args=(incident.id,),
                            daemon=True,
                        ).start()
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
