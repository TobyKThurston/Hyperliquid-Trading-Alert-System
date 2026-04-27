"""Alert endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional
from api.dependencies import get_db
from api.models.alert import AlertResponse, AlertListResponse
from api.models.delivery import DeliveryAttemptListResponse, DeliveryAttemptResponse
from db.models import Alert, AlertDeliveryAttempt

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


@router.get("/{alert_id}/deliveries", response_model=DeliveryAttemptListResponse)
async def list_delivery_attempts(
    alert_id: UUID,
    limit: int = Query(50, ge=1, le=200),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> DeliveryAttemptListResponse:
    """Return delivery attempts for an alert, most recent first.

    404 if the alert itself doesn't exist. Returns an empty list if the
    alert exists but nothing has been dispatched yet.
    """
    alert_exists = await db.execute(select(Alert.id).where(Alert.id == alert_id))
    if alert_exists.scalar_one_or_none() is None:
        raise HTTPException(status_code=404, detail="Alert not found")

    count_result = await db.execute(
        select(func.count())
        .select_from(AlertDeliveryAttempt)
        .where(AlertDeliveryAttempt.alert_id == alert_id)
    )
    total = count_result.scalar() or 0

    result = await db.execute(
        select(AlertDeliveryAttempt)
        .where(AlertDeliveryAttempt.alert_id == alert_id)
        .order_by(AlertDeliveryAttempt.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    attempts = result.scalars().all()

    return DeliveryAttemptListResponse(
        attempts=[DeliveryAttemptResponse.model_validate(a) for a in attempts],
        total=total,
    )

