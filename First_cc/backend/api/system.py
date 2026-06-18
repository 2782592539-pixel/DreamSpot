"""System status endpoint - health check."""
from datetime import datetime, timezone
from fastapi import APIRouter

router = APIRouter(prefix="/api/system", tags=["system"])


@router.get("/status")
def get_status() -> dict:
    """Return service health status."""
    return {
        "status": "ok",
        "service": "mzc",
        "version": "0.1.0",
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }
