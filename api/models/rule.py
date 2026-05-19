"""Rule API models."""

from datetime import datetime
from typing import Literal
from uuid import UUID

from pydantic import BaseModel, ConfigDict, Field, field_validator

RuleType = Literal[
    "price_threshold",
    "percent_move",
    "candle_close",
    "macd_cross",
    "rsi",
    "bollinger_bands",
]


class RuleCreate(BaseModel):
    """Request model for creating a rule."""

    name: str = Field(..., min_length=1, max_length=200)
    rule_type: RuleType
    symbol: str = Field(..., min_length=1, max_length=20)
    config: dict = Field(..., description="Rule-specific configuration")
    cooldown_seconds: int = Field(default=0, ge=0)
    discord_webhook_url: str | None = Field(None, max_length=500)
    generic_webhook_url: str | None = Field(None, max_length=500)
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
                raise ValueError(
                    "macd_cross requires 'fast_period', 'slow_period', and 'signal_period'"
                )
            if "crossover_type" not in v:
                raise ValueError("macd_cross requires 'crossover_type'")
            if v["crossover_type"] not in ("bullish", "bearish"):
                raise ValueError("crossover_type must be 'bullish' or 'bearish'")
        elif rule_type == "rsi":
            if "direction" not in v:
                raise ValueError("rsi requires 'direction' ('overbought' or 'oversold')")
            if v["direction"] not in ("overbought", "oversold"):
                raise ValueError("direction must be 'overbought' or 'oversold'")
        elif rule_type == "bollinger_bands":
            if "band" not in v or "event" not in v:
                raise ValueError("bollinger_bands requires 'band' and 'event'")
            if v["band"] not in ("upper", "lower"):
                raise ValueError("band must be 'upper' or 'lower'")
            if v["event"] not in ("touch", "break"):
                raise ValueError("event must be 'touch' or 'break'")

        return v


class RuleUpdate(BaseModel):
    """Request model for updating a rule."""

    name: str | None = Field(None, min_length=1, max_length=200)
    config: dict | None = None
    cooldown_seconds: int | None = Field(None, ge=0)
    discord_webhook_url: str | None = Field(None, max_length=500)
    generic_webhook_url: str | None = Field(None, max_length=500)
    is_active: bool | None = None


class RuleResponse(BaseModel):
    """Response model for a rule."""

    id: UUID
    name: str
    rule_type: RuleType
    symbol: str
    config: dict
    cooldown_seconds: int
    discord_webhook_url: str | None
    generic_webhook_url: str | None
    is_active: bool
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)


class RuleListResponse(BaseModel):
    """Response model for listing rules."""

    rules: list[RuleResponse]
    total: int
