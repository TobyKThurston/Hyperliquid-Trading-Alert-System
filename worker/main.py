"""Worker main entry point."""
import asyncio

from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import make_transient

from core.logging import configure_logging, get_logger
from db.base import AsyncSessionLocal
from db.models import Candle as CandleModel
from db.models import Rule
from worker.config import settings
from worker.dispatch.dispatcher import AlertDispatcher
from worker.dispatch.retry import retry_scheduler
from worker.evaluate.engine import RuleEvaluator
from worker.ingest.cursor import get_all_cursors, update_cursor
from worker.ingest.hyperliquid import Candle, HyperliquidClient

configure_logging(settings.log_level)
logger = get_logger(__name__)


async def save_candle(db, candle: Candle) -> None:
    """Persist candle; swallow duplicate-key errors (backfill overlap)."""
    db_candle = CandleModel(
        symbol=candle.symbol,
        timestamp=candle.timestamp,
        open=candle.open,
        high=candle.high,
        low=candle.low,
        close=candle.close,
        volume=candle.volume,
        interval_seconds=candle.interval_seconds,
    )
    db.add(db_candle)
    try:
        await db.commit()
    except IntegrityError:
        await db.rollback()
        logger.debug(
            "candle_duplicate_skipped",
            symbol=candle.symbol,
            timestamp=candle.timestamp.isoformat(),
        )


async def load_active_rules(db) -> list[dict]:
    """Snapshot active rules as dicts — avoids ORM lazy-load after session close."""
    result = await db.execute(select(Rule).where(Rule.is_active == True))  # noqa: E712
    rules = result.scalars().all()
    return [
        {
            "id": r.id,
            "symbol": r.symbol,
            "rule_type": r.rule_type,
            "config": r.config,
            "cooldown_seconds": r.cooldown_seconds,
            "is_active": r.is_active,
            "discord_webhook_url": r.discord_webhook_url,
            "generic_webhook_url": r.generic_webhook_url,
        }
        for r in rules
    ]


async def main_loop() -> None:
    """Run the ingest → evaluate → dispatch pipeline.

    The WS client handles reconnect + gap-backfill internally, so this loop
    stays simple: pull candles forever, evaluate, dispatch. A background
    retry scheduler re-drives failed deliveries.
    """
    logger.info(
        "worker_starting",
        worker_id=settings.worker_id,
        symbols=settings.symbol_list,
        mode=settings.ingest_mode,
    )

    hyperliquid = HyperliquidClient()
    retry_task: asyncio.Task | None = None

    try:
        async with AsyncSessionLocal() as db:
            rules = await load_active_rules(db)
            logger.info("loaded_rules", count=len(rules))

            cursors = await get_all_cursors(db)
            logger.info("loaded_cursors", cursors=list(cursors.keys()))
            hyperliquid.seed_last_seen(cursors)

            evaluator = RuleEvaluator(db)
            dispatcher = AlertDispatcher(db)

            await hyperliquid.connect()
            retry_task = asyncio.create_task(retry_scheduler())

            async for candle in hyperliquid.stream():
                await save_candle(db, candle)
                await update_cursor(db, candle.symbol, candle.timestamp)

                symbol_rules = [
                    r for r in rules if r["symbol"] == candle.symbol and r["is_active"]
                ]
                for rule_dict in symbol_rules:
                    try:
                        rule = Rule(
                            id=rule_dict["id"],
                            symbol=rule_dict["symbol"],
                            rule_type=rule_dict["rule_type"],
                            config=rule_dict["config"],
                            cooldown_seconds=rule_dict["cooldown_seconds"],
                            is_active=rule_dict["is_active"],
                            discord_webhook_url=rule_dict.get("discord_webhook_url"),
                            generic_webhook_url=rule_dict.get("generic_webhook_url"),
                        )
                        make_transient(rule)

                        alert = await evaluator.evaluate(rule, candle)
                        if alert:
                            await dispatcher.dispatch(alert)
                    except Exception as e:
                        logger.error(
                            "rule_evaluation_failed",
                            rule_id=str(rule_dict["id"]),
                            symbol=candle.symbol,
                            error=str(e),
                            exc_info=True,
                        )
                        # Failed eval/dispatch can leave the session in a
                        # failed-transaction state; roll back so the next
                        # candle doesn't silently fail at commit time.
                        await db.rollback()
    except asyncio.CancelledError:
        logger.info("worker_cancelled")
        raise
    except Exception as e:
        logger.error("worker_fatal_error", error=str(e), exc_info=True)
        raise
    finally:
        if retry_task:
            retry_task.cancel()
            try:
                await retry_task
            except asyncio.CancelledError:
                pass
        await hyperliquid.close()


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("worker_stopped")
