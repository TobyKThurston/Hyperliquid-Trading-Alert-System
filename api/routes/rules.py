"""Rule management endpoints."""
from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func
from uuid import UUID
from typing import Optional
from api.dependencies import get_db, verify_api_key
from api.models.rule import RuleCreate, RuleUpdate, RuleResponse, RuleListResponse
from db.models import Rule
from core.exceptions import RuleNotFoundError

router = APIRouter(prefix="/rules", tags=["rules"])


@router.post("", response_model=RuleResponse, status_code=201)
async def create_rule(
    rule_data: RuleCreate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key),
) -> RuleResponse:
    """Create a new alert rule."""
    rule = Rule(
        name=rule_data.name,
        rule_type=rule_data.rule_type,
        symbol=rule_data.symbol.upper(),
        config=rule_data.config,
        cooldown_seconds=rule_data.cooldown_seconds,
        discord_webhook_url=rule_data.discord_webhook_url,
        generic_webhook_url=rule_data.generic_webhook_url,
        is_active=rule_data.is_active,
    )
    db.add(rule)
    await db.commit()
    await db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.get("", response_model=RuleListResponse)
async def list_rules(
    symbol: Optional[str] = Query(None),
    is_active: Optional[bool] = Query(None),
    limit: int = Query(50, ge=1, le=100),
    offset: int = Query(0, ge=0),
    db: AsyncSession = Depends(get_db),
) -> RuleListResponse:
    """List alert rules with optional filtering."""
    query = select(Rule)
    
    if symbol:
        query = query.where(Rule.symbol == symbol.upper())
    if is_active is not None:
        query = query.where(Rule.is_active == is_active)
    
    # Get total count
    count_query = select(func.count()).select_from(query.subquery())
    total_result = await db.execute(count_query)
    total = total_result.scalar() or 0
    
    # Get paginated results
    query = query.order_by(Rule.created_at.desc()).limit(limit).offset(offset)
    result = await db.execute(query)
    rules = result.scalars().all()
    
    return RuleListResponse(
        rules=[RuleResponse.model_validate(rule) for rule in rules],
        total=total,
    )


@router.get("/{rule_id}", response_model=RuleResponse)
async def get_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
) -> RuleResponse:
    """Get a specific rule by ID."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    return RuleResponse.model_validate(rule)


@router.put("/{rule_id}", response_model=RuleResponse)
async def update_rule(
    rule_id: UUID,
    rule_data: RuleUpdate,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key),
) -> RuleResponse:
    """Update an existing rule."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    # Update fields
    update_data = rule_data.model_dump(exclude_unset=True)
    for field, value in update_data.items():
        setattr(rule, field, value)
    
    await db.commit()
    await db.refresh(rule)
    return RuleResponse.model_validate(rule)


@router.delete("/{rule_id}", status_code=204)
async def delete_rule(
    rule_id: UUID,
    db: AsyncSession = Depends(get_db),
    _: bool = Depends(verify_api_key),
) -> None:
    """Delete a rule."""
    result = await db.execute(select(Rule).where(Rule.id == rule_id))
    rule = result.scalar_one_or_none()
    
    if not rule:
        raise HTTPException(status_code=404, detail="Rule not found")
    
    await db.delete(rule)
    await db.commit()

