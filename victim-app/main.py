import logging

from fastapi import FastAPI, HTTPException

logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(message)s")
logger = logging.getLogger("victim-app")

app = FastAPI()

is_broken = False

ORDERS = [
    {"id": 1, "item": "Widget", "quantity": 3},
    {"id": 2, "item": "Gadget", "quantity": 1},
]


@app.get("/health")
def health():
    if is_broken:
        logger.error("Health check failed: dependency unavailable")
        raise HTTPException(status_code=500, detail="dependency unavailable")
    logger.info("Health check OK")
    return {"status": "healthy"}


@app.get("/orders")
def orders():
    if is_broken:
        logger.error("Orders fetch failed: connection refused")
        raise HTTPException(status_code=500, detail="connection refused")
    logger.info("Orders fetched OK")
    return ORDERS


@app.post("/admin/break")
def admin_break():
    global is_broken
    is_broken = True
    logger.info("Admin: victim-app broken")
    return {"status": "broken"}


@app.post("/admin/fix")
def admin_fix():
    global is_broken
    is_broken = False
    logger.info("Admin: victim-app fixed")
    return {"status": "fixed"}
