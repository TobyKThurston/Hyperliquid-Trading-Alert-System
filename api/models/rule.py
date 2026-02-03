"""Rule API models."""
from pydantic import BaseModel, Field, field_validator
from typing import Optional, Literal
from datetime import datetime
from uuid import UUID


RuleType = Literal["price_threshold", "percent_move", "candle_close", "macd_cross"]


class RuleCreate(BaseModel):
    """Request model for creating a rule."""

    name: str = Field(..., min_length=1, max_length=200)
    rule_type: RuleType
    symbol: str = Field(..., min_length=1, max_length=20)
    config: dict = Field(..., description="Rule-specific configuration")
    cooldown_seconds: int = Field(default=0, ge=0)
    discord_webhook_url: Optional[str] = Field(None, max_length=500)
    generic_webhook_url: Optional[str] = Field(None, max_length=500)
    is_active: bool = Field(default=True)

    @field_validator("config")
    @classmethod
    def validate_config(cls, v: dict, info) -> dict:
        """Validate rule config based on rule_type."""
        rule_type = info.data.get("rule_type")
        if not rule_type:
            return v
        
        if rule_type == "price_threshold":
            if "threshold" not in v or "operator" not in v:
                raise ValueError("price_threshold requires 'threshold' and 'operator'")
            if v["operator"] not in (">=", "<="):
                raise ValueError("operator must be '>=' or '<='")
        elif rule_type == "percent_move":
            if "percent_threshold" not in v or "window_seconds" not in v:
                raise ValueError("percent_move requires 'percent_threshold' and 'window_seconds'")
        elif rule_type == "candle_close":
            if "value" not in v or "operator" not in v:
                raise ValueError("candle_close requires 'value' and 'operator'")
            if v["operator"] not in (">=", "<="):
                raise ValueError("operator must be '>=' or '<='")
        elif rule_type == "macd_cross":
            if "fast_period" not in v or "slow_period" not in v or "signal_period" not in v:
                raise ValueError("macd_cross requires 'fast_period', 'slow_period', and 'signal_period'")
            if "crossover_type" not in v:
                raise ValueError("macd_cross requires 'crossover_type'")
            if v["crossover_type"] not in ("bullish", "bearish"):
                raise ValueError("crossover_type must be 'bullish' or 'bearish'")
        
        return v


class RuleUpdate(BaseModel):
    """Request model for updating a rule."""

    name: Optional[str] = Field(None, min_length=1, max_length=200)
    config: Optional[dict] = None
    cooldown_seconds: Optional[int] = Field(None, ge=0)
    discord_webhook_url: Optional[str] = Field(None, max_length=500)
    generic_webhook_url: Optional[str] = Field(None, max_length=500)
    is_active: Optional[bool] = None


class RuleResponse(BaseModel):
    """Response model for a rule."""

    id: UUID
    name: str
    rule_type: RuleType
    symbol: str
    config: dict
    cooldown_seconds: int
    discord_webhook_url: Optional[str]
    generic_webhook_url: Optional[str]
    is_active: bool
    created_at: datetime
    updated_at: datetime

    class Config:
        from_attributes = True


class RuleListResponse(BaseModel):
    """Response model for listing rules."""

    rules: list[RuleResponse]
    total: int

