"""Base rule class."""

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncSession

from worker.ingest.hyperliquid import Candle


class BaseRule(ABC):
    """Abstract base class for rule evaluation."""

    @abstractmethod
    async def evaluate(self, config: dict, candle: Candle, db: AsyncSession) -> float | None:
        """
        Evaluate rule against candle data.

        Returns:
            Trigger value if rule matches, None otherwise.
        """
        pass
