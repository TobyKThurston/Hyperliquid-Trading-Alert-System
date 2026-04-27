"""Retry scheduler for failed alert deliveries."""
import asyncio
import random
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from db.models import Alert, Rule, AlertDeliveryAttempt
from db.base import AsyncSessionLocal
from worker.dispatch.discord import send_discord_webhook
from worker.dispatch.webhook import send_generic_webhook
from worker.config import settings
from core.logging import get_logger
from core.time import utcnow

logger = get_logger(__name__)


def calculate_backoff(attempts: int) -> float:
    """Exponential backoff with up to 50% jitter, capped at 32s base."""
    base = min(2 ** (attempts - 1), 32)
    return base + random.uniform(0, base * 0.5)


async def process_pending_alerts() -> None:
    """Process pending alerts with exponential backoff retry."""
    async with AsyncSessionLocal() as db:
        result = await db.execute(
            select(Alert)
            .where(
                Alert.delivery_status == "pending",
                Alert.delivery_attempts < settings.retry_backoff_max,
            )
            .order_by(Alert.created_at.asc())
            .limit(50)
        )
        alerts = result.scalars().all()

        for alert in alerts:
            now = utcnow()
            if alert.last_delivery_attempt:
                backoff_seconds = calculate_backoff(alert.delivery_attempts)
                next_attempt_time = alert.last_delivery_attempt + timedelta(
                    seconds=backoff_seconds
                )
                if now < next_attempt_time:
                    continue

            rule_result = await db.execute(
                select(Rule).where(Rule.id == alert.rule_id)
            )
            rule = rule_result.scalar_one_or_none()

            if not rule:
                logger.warn("rule_not_found_for_alert", alert_id=str(alert.id))
                alert.delivery_status = "failed"
                await db.commit()
                continue

            alert.delivery_attempts += 1
            alert.last_delivery_attempt = now
            attempt_no = alert.delivery_attempts
            start_time = utcnow()

            attempt = AlertDeliveryAttempt(
                alert_id=alert.id,
                attempt_no=attempt_no,
                status="failed",
                created_at=start_time,
            )
            db.add(attempt)

            success = False
            response_code = None
            error = None

            try:
                if rule.discord_webhook_url:
                    success = await send_discord_webhook(alert, rule)
                    if success:
                        response_code = 200
                if not success and rule.generic_webhook_url:
                    success = await send_generic_webhook(alert, rule)
                    if success:
                        response_code = 200
            except Exception as e:
                error = str(e)
                logger.error("retry_delivery_exception", alert_id=str(alert.id), error=str(e))

            end_time = utcnow()
            latency_ms = int((end_time - start_time).total_seconds() * 1000)
            attempt.status = "success" if success else "failed"
            attempt.response_code = response_code
            attempt.latency_ms = latency_ms
            attempt.error = error

            if success:
                alert.delivery_status = "delivered"
                logger.info("alert_delivered_retry", alert_id=str(alert.id), attempts=attempt_no)
            elif alert.delivery_attempts >= settings.retry_backoff_max:
                alert.delivery_status = "failed"
                logger.error(
                    "alert_failed_max_retries",
                    alert_id=str(alert.id),
                    attempts=alert.delivery_attempts,
                )

            await db.commit()


async def retry_scheduler() -> None:
    """Background task that polls for pending alerts and retries delivery."""
    logger.info("retry_scheduler_started", poll_interval=settings.retry_poll_interval)
    while True:
        try:
            await process_pending_alerts()
        except Exception as e:
            logger.error("retry_scheduler_error", error=str(e), exc_info=True)

        await asyncio.sleep(settings.retry_poll_interval)

