"""Generic webhook dispatcher."""
import httpx
from db.models import Alert, Rule
from core.logging import get_logger

logger = get_logger(__name__)


async def send_generic_webhook(alert: Alert, rule: Rule) -> bool:
    """Send alert to generic webhook."""
    if not rule.generic_webhook_url:
        return False

    payload = {
        "alert_id": str(alert.id),
        "rule_id": str(rule.id),
        "rule_name": rule.name,
        "symbol": alert.symbol,
        "rule_type": alert.rule_type,
        "trigger_value": float(alert.trigger_value) if alert.trigger_value else None,
        "triggered_at": alert.triggered_at.isoformat() + "Z",
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(rule.generic_webhook_url, json=payload)
            response.raise_for_status()
            logger.info("generic_webhook_sent", alert_id=str(alert.id))
            return True
    except Exception as e:
        logger.error(
            "generic_webhook_failed",
            alert_id=str(alert.id),
            error=str(e),
        )
        return False

