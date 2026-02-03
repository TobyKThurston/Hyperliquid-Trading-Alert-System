"""Alert endpoints."""
from fastapi import APIRouter, Depends, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional
from api.dependencies import get_db
from api.models.alert import AlertResponse, AlertListResponse
from db.models import Alert

router = APIRouter(prefix="/alerts", tags=["alerts"])


@router.get("", response_model=AlertListResponse)
async def list_alerts(
    rule_id: Optional[UUID] = Query(None),
    symbol: Optional[str] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> AlertListResponse:
    """List alerts with optional filtering."""
    query = select(Alert)
    
    if rule_id:
        query = query.where(Alert.rule_id == rule_id)
    if symbol:
        query = query.where(Alert.symbol == symbol.upper())
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    query = query.order_by(Alert.triggered_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    alerts = result.scalars().all()
    
    return AlertListResponse(
        alerts=[AlertResponse.model_validate(alert) for alert in alerts],
        total=total,
    )

