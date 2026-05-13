from datetime import datetime, timezone

from fastapi import APIRouter, Depends
from sqlalchemy import text
from sqlalchemy.orm import Session

from app.db.session import get_db
from app.dependencies.auth import require_roles
from app.schemas.common import Role
from app.services.cache import cache_service
from app.services.metrics import metrics_store

router = APIRouter(prefix="/monitoring", tags=["monitoring"])


@router.get("/health")
def health(db: Session = Depends(get_db)):
    database_status = "ok"
    try:
        db.execute(text("SELECT 1"))
    except Exception as exc:
        database_status = f"error: {exc}"
    cache_status = cache_service.ping()
    status = "healthy" if database_status == "ok" and cache_status["status"] == "ok" else "degraded"
    return {
        "status": status,
        "database": database_status,
        "cache": cache_status,
        "timestamp": datetime.now(timezone.utc).isoformat(),
    }


@router.get("/metrics", dependencies=[Depends(require_roles(Role.admin))])
def metrics():
    return metrics_store.snapshot(cache_service.stats())


@router.get("/logs", dependencies=[Depends(require_roles(Role.admin))])
def logs():
    return {"logs": metrics_store.snapshot(cache_service.stats())["recent_logs"]}
