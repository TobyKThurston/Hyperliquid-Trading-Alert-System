"""Worker main entry point."""
import asyncio
import websockets.exceptions
from datetime import datetime
from sqlalchemy import select
from db.base import AsyncSessionLocal
from db.models import Rule, Candle as CandleModel
from worker.config import settings
from worker.ingest.hyperliquid import HyperliquidClient, Candle
from worker.ingest.cursor import update_cursor, get_all_cursors
from worker.evaluate.engine import RuleEvaluator
from worker.dispatch.dispatcher import AlertDispatcher
from worker.dispatch.retry import retry_scheduler
from core.logging import configure_logging, get_logger

# Configure logging
configure_logging(settings.log_level)
logger = get_logger(__name__)


async def save_candle(db, candle: Candle) -> None:
    """Save candle to database."""
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
    except Exception:
        # Ignore duplicate key errors (unique constraint)
        await db.rollback()


async def load_active_rules(db) -> list[dict]:
    """Load active rules as dicts to avoid ORM lazy loading after session closes."""
    result = await db.execute(select(Rule).where(Rule.is_active == True))
    rules = result.scalars().all()

    rule_dicts = []
    for rule in rules:
        rule_dicts.append({
            "id": rule.id,
            "symbol": rule.symbol,
            "rule_type": rule.rule_type,
            "config": rule.config,
            "cooldown_seconds": rule.cooldown_seconds,
            "is_active": rule.is_active,
            "discord_webhook_url": rule.discord_webhook_url,
            "generic_webhook_url": rule.generic_webhook_url,
        })

    return rule_dicts


async def backfill_missing_candles(
    db, hyperliquid: HyperliquidClient, cursors: dict[str, datetime]
) -> None:
    """Backfill missing candles after disconnect."""
    logger.info("backfilling_candles", cursors=list(cursors.keys()))
    
    for coin, last_timestamp in cursors.items():
        try:
            candles = await hyperliquid.backfill(coin, last_timestamp)
            logger.info("backfilled_candles", coin=coin, count=len(candles))
            
            for candle in candles:
                await save_candle(db, candle)
                await update_cursor(db, coin, candle.timestamp)
        except Exception as e:
            logger.error("backfill_failed", coin=coin, error=str(e), exc_info=True)


async def main_loop() -> None:
    """Main worker loop."""
    logger.info("worker_starting", worker_id=settings.worker_id, symbols=settings.symbol_list)
    
    hyperliquid = HyperliquidClient()
    
    try:
        async with AsyncSessionLocal() as db:
            # Load active rules
            rules = await load_active_rules(db)
            logger.info("loaded_rules", count=len(rules))
            
            # Load cursors
            cursors = await get_all_cursors(db)
            logger.info("loaded_cursors", cursors=list(cursors.keys()))
            
            # Initialize components
            evaluator = RuleEvaluator(db)
            dispatcher = AlertDispatcher(db)
            
            # Connect WebSocket
            await hyperliquid.connect()
            
            # Start retry scheduler in background
            retry_task = asyncio.create_task(retry_scheduler())
            
            try:
                # Stream candles
                async for candle in hyperliquid.stream():
                    # Save candle
                    await save_candle(db, candle)
                    
                    # Update cursor
                    await update_cursor(db, candle.symbol, candle.timestamp)
                    
                    # Evaluate rules for this symbol
                    symbol_rules = [
                        r for r in rules if r["symbol"] == candle.symbol and r["is_active"]
                    ]
                    
                    for rule_dict in symbol_rules:
                        try:
                            from sqlalchemy.orm import make_transient
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
                            
            except websockets.exceptions.ConnectionClosed:
                logger.warn("websocket_disconnected", action="backfilling")
                await backfill_missing_candles(db, hyperliquid, cursors)
                # Reconnect and continue
                await hyperliquid.connect()
            except KeyboardInterrupt:
                logger.info("worker_shutting_down")
                retry_task.cancel()
                try:
                    await retry_task
                except asyncio.CancelledError:
                    pass
            finally:
                await hyperliquid.close()
                
    except Exception as e:
        logger.error("worker_fatal_error", error=str(e), exc_info=True)
        raise


if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        logger.info("worker_stopped")

