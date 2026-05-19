"""Discord webhook dispatcher."""

import httpx

from core.logging import get_logger
from db.models import Alert, Rule

logger = get_logger(__name__)


async def send_discord_webhook(alert: Alert, rule: Rule) -> bool:
    """Send alert to Discord webhook."""
    if not rule.discord_webhook_url:
        return False

    payload = {
        "embeds": [
            {
                "title": f"Alert: {rule.name}",
                "description": f"{alert.symbol} triggered at {alert.trigger_value}",
                "color": 0x00FF00,  # Green
                "fields": [
                    {"name": "Symbol", "value": alert.symbol, "inline": True},
                    {"name": "Trigger Value", "value": str(alert.trigger_value), "inline": True},
                    {"name": "Rule Type", "value": alert.rule_type, "inline": True},
                    {
                        "name": "Time",
                        "value": alert.triggered_at.isoformat() + "Z",
                        "inline": False,
                    },
                ],
            }
        ]
    }

    try:
        async with httpx.AsyncClient(timeout=10.0) as client:
            response = await client.post(rule.discord_webhook_url, json=payload)
            response.raise_for_status()
            logger.info("discord_webhook_sent", alert_id=str(alert.id))
            return True
    except Exception as e:
        logger.error(
            "discord_webhook_failed",
            alert_id=str(alert.id),
            error=str(e),
        )
        return False
