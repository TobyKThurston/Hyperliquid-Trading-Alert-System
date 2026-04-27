"""Health check endpoints."""
from fastapi import APIRouter, Depends
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import text
from api.dependencies import get_db
from core.time import utcnow

router = APIRouter()


@router.get("/health")
async def health_check() -> dict:
    """Basic health check endpoint."""
    return {"status": "healthy", "timestamp": utcnow().isoformat() + "Z"}


@router.get("/metrics")
async def metrics(db: AsyncSession = Depends(get_db)) -> dict:
    """Basic metrics endpoint."""
    from sqlalchemy import select, func
    from db.models import Rule, Alert
    
    # Count active rules
    active_rules_result = await db.execute(
        select(func.count()).select_from(Rule).where(Rule.is_active == True)
    )
    active_rules = active_rules_result.scalar() or 0
    
    # Count pending alerts
    pending_alerts_result = await db.execute(
        select(func.count()).select_from(Alert).where(Alert.delivery_status == "pending")
    )
    pending_alerts = pending_alerts_result.scalar() or 0
    
    # Check DB connection
    try:
        await db.execute(text("SELECT 1"))
        db_status = "connected"
    except Exception:
        db_status = "disconnected"
    
    return {
        "rules_active": active_rules,
        "alerts_pending_delivery": pending_alerts,
        "database_status": db_status,
    }

