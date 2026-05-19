"""Alert dispatcher."""

from datetime import datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from core.logging import get_logger
from core.time import utcnow
from db.models import Alert, AlertDeliveryAttempt, Rule
from worker.dispatch.discord import send_discord_webhook
from worker.dispatch.webhook import send_generic_webhook

logger = get_logger(__name__)


class AlertDispatcher:
    """Dispatches alerts to Discord and generic webhooks.

    Records delivery attempts with latency and response codes for observability.
    """

    def __init__(self, db: AsyncSession):
        self.db = db

    async def _create_delivery_attempt(
        self, alert: Alert, attempt_no: int, start_time: datetime
    ) -> AlertDeliveryAttempt:
        """Create delivery attempt record."""
        attempt = AlertDeliveryAttempt(
            alert_id=alert.id,
            attempt_no=attempt_no,
            status="failed",
            created_at=start_time,
        )
        self.db.add(attempt)
        return attempt

    async def _update_delivery_attempt(
        self,
        attempt: AlertDeliveryAttempt,
        success: bool,
        response_code: int | None = None,
        latency_ms: int | None = None,
        error: str | None = None,
    ) -> None:
        """Update delivery attempt with result."""
        attempt.status = "success" if success else "failed"
        attempt.response_code = response_code
        attempt.latency_ms = latency_ms
        attempt.error = error

    async def dispatch(self, alert: Alert) -> None:
        """Dispatch alert to configured webhooks.

        Tries Discord first, then generic webhook. Marks as pending for retry if all fail.
        """
        result = await self.db.execute(select(Rule).where(Rule.id == alert.rule_id))
        rule = result.scalar_one_or_none()

        if not rule:
            logger.warn("rule_not_found_for_alert", alert_id=str(alert.id))
            return

        attempt_no = alert.delivery_attempts + 1
        start_time = utcnow()
        # Record the attempt time on the alert so retry backoff can key off it
        # even when every channel fails. (Previously left None on failure, which
        # caused retry.py to skip its backoff check on the first retry.)
        alert.last_delivery_attempt = start_time

        if rule.discord_webhook_url:
            attempt = await self._create_delivery_attempt(alert, attempt_no, start_time)

            try:
                success = await send_discord_webhook(alert, rule)
                end_time = utcnow()
                latency_ms = int((end_time - start_time).total_seconds() * 1000)
                response_code = 200 if success else None

                await self._update_delivery_attempt(
                    attempt, success=success, response_code=response_code, latency_ms=latency_ms
                )

                if success:
                    alert.delivery_status = "delivered"
                    alert.delivery_attempts = attempt_no
                    await self.db.commit()
                    logger.info("alert_delivered", alert_id=str(alert.id), channel="discord")
                    return
            except Exception as e:
                end_time = utcnow()
                latency_ms = int((end_time - start_time).total_seconds() * 1000)
                await self._update_delivery_attempt(
                    attempt, success=False, latency_ms=latency_ms, error=str(e)
                )
                logger.error("discord_dispatch_exception", alert_id=str(alert.id), error=str(e))

        if rule.generic_webhook_url:
            attempt = await self._create_delivery_attempt(alert, attempt_no, start_time)

            try:
                success = await send_generic_webhook(alert, rule)
                end_time = utcnow()
                latency_ms = int((end_time - start_time).total_seconds() * 1000)
                response_code = 200 if success else None

                await self._update_delivery_attempt(
                    attempt, success=success, response_code=response_code, latency_ms=latency_ms
                )

                if success:
                    alert.delivery_status = "delivered"
                    alert.delivery_attempts = attempt_no
                    await self.db.commit()
                    logger.info("alert_delivered", alert_id=str(alert.id), channel="generic")
                    return
            except Exception as e:
                end_time = utcnow()
                latency_ms = int((end_time - start_time).total_seconds() * 1000)
                await self._update_delivery_attempt(
                    attempt, success=False, latency_ms=latency_ms, error=str(e)
                )
                logger.error(
                    "generic_webhook_dispatch_exception", alert_id=str(alert.id), error=str(e)
                )

        alert.delivery_status = "pending"
        alert.delivery_attempts = attempt_no
        await self.db.commit()
        logger.debug("alert_pending_retry", alert_id=str(alert.id), attempts=attempt_no)
