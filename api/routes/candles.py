"""Candle endpoints."""
from fastapi import APIRouter, Depends, Query, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from datetime import datetime
from typing import Optional
from api.dependencies import get_db
from api.models.candle import CandleResponse, CandleListResponse
from db.models import Candle
from core.logging import get_logger

logger = get_logger(__name__)

router = APIRouter(prefix="/candles", tags=["candles"])


@router.get("", response_model=CandleListResponse)
async def list_candles(
    symbol: str = Query(..., min_length=1, max_length=20, description="Symbol (e.g., BTC, ETH)"),
    interval_seconds: int = Query(900, ge=60, description="Candle interval in seconds"),
    start_time: Optional[datetime] = Query(None, description="Start time (ISO8601)"),
    end_time: Optional[datetime] = Query(None, description="End time (ISO8601)"),
    limit: int = Query(200, ge=1, le=500, description="Maximum number of candles to return"),
    offset: int = Query(0, ge=0, le=100000, description="Number of candles to skip"),
    order: str = Query("desc", pattern="^(asc|desc)$", description="Sort order: asc or desc"),
    db: AsyncSession = Depends(get_db),
) -> CandleListResponse:
    """List candles with optional filtering."""
    symbol_upper = symbol.upper()
    
    logger.debug(
        "listing_candles",
        symbol=symbol_upper,
        interval_seconds=interval_seconds,
        start_time=start_time.isoformat() if start_time else None,
        end_time=end_time.isoformat() if end_time else None,
        limit=limit,
        offset=offset,
        order=order,
    )
    
    # Build query
    query = select(Candle).where(Candle.symbol == symbol_upper)
    query = query.where(Candle.interval_seconds == interval_seconds)
    
    if start_time:
        query = query.where(Candle.timestamp >= start_time)
    if end_time:
        query = query.where(Candle.timestamp <= end_time)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Order and paginate
    order_by_clause = Candle.timestamp.desc() if order == "desc" else Candle.timestamp.asc()
    query = query.order_by(order_by_clause).limit(limit).offset(offset)
    
    result = await db.execute(query)
    candles = result.scalars().all()
    
    logger.info("candles_listed", symbol=symbol_upper, count=len(candles), total=total)
    
    return CandleListResponse(
        candles=[CandleResponse.model_validate(candle) for candle in candles],
        total=total,
        limit=limit,
        offset=offset,
        order=order,
    )

