"""Hyperliquid REST API client for candle data."""
import asyncio
from datetime import datetime
from typing import AsyncIterator, Optional
from decimal import Decimal
import httpx
from core.logging import get_logger
from worker.config import settings

logger = get_logger(__name__)


class Candle:
    """OHLCV candle data structure."""

    def __init__(
        self,
        symbol: str,
        timestamp: datetime,
        open: Decimal,
        high: Decimal,
        low: Decimal,
        close: Decimal,
        volume: Optional[Decimal] = None,
        interval_seconds: int = 900,
    ):
        self.symbol = symbol.upper()
        self.timestamp = timestamp
        self.open = Decimal(str(open))
        self.high = Decimal(str(high))
        self.low = Decimal(str(low))
        self.close = Decimal(str(close))
        self.volume = Decimal(str(volume)) if volume else None
        self.interval_seconds = interval_seconds


class HyperliquidClient:
    """Client for Hyperliquid REST API.

    Polls /info endpoint for candle data. Uses rolling window to fetch latest candles.
    """

    def __init__(self):
        self.rest_url = settings.hyperliquid_rest_url
        self.symbols = settings.symbol_list

    async def connect(self) -> None:
        """Placeholder for WebSocket connection (not used currently)."""
        logger.info("hyperliquid_client_initialized", symbols=self.symbols)

    async def fetch_latest_candle(self, coin: str) -> Optional[Candle]:
        """Fetch latest candle for a coin using rolling window.

        Requests last 200 candles and returns the most recent one.
        """
        INTERVAL_MS = 15 * 60 * 1000  # 15 minutes
        CANDLES_BACK = 200  # Fetch last 200 candles
        
        end_time_ms = int(datetime.utcnow().timestamp() * 1000)
        start_time_ms = end_time_ms - (CANDLES_BACK * INTERVAL_MS)
        
        try:
            url = f"{self.rest_url}/info"
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": coin.upper(),
                    "interval": "15m",
                    "startTime": start_time_ms,
                    "endTime": end_time_ms,
                },
            }
            
            async with httpx.AsyncClient(timeout=10.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                
                if response.status_code != 200:
                    response_text = response.text[:500]  # Limit response body length
                    logger.error(
                        "fetch_latest_candle_failed",
                        coin=coin,
                        interval="15m",
                        startTime=start_time_ms,
                        endTime=end_time_ms,
                        http_status=response.status_code,
                        response_body=response_text,
                    )
                    return None
                
                data = response.json()
                
                # Hyperliquid returns array of candles directly
                candles_data = data if isinstance(data, list) else data.get("data", [])
                if not candles_data:
                    logger.debug("no_candles_returned", coin=coin)
                    return None

                def get_timestamp_ms(candle_dict):
                    return (
                        candle_dict.get("t") or
                        candle_dict.get("time") or
                        candle_dict.get("timestamp") or
                        None
                    )

                candles_data = sorted(candles_data, key=lambda x: get_timestamp_ms(x) or 0)
                latest = candles_data[-1]

                ts_ms = get_timestamp_ms(latest)
                if ts_ms is None:
                    raise KeyError(f"no timestamp key in candle: keys={list(latest.keys())}")

                timestamp = datetime.fromtimestamp(ts_ms / 1000)

                open_price = latest.get("o") or latest.get("open")
                high_price = latest.get("h") or latest.get("high")
                low_price = latest.get("l") or latest.get("low")
                close_price = latest.get("c") or latest.get("close")
                volume = latest.get("v") or latest.get("volume") or 0

                if open_price is None or high_price is None or low_price is None or close_price is None:
                    raise KeyError(f"missing OHLC fields: keys={list(latest.keys())}")

                candle = Candle(
                    symbol=coin.upper(),
                    timestamp=timestamp,
                    open=Decimal(str(open_price)),
                    high=Decimal(str(high_price)),
                    low=Decimal(str(low_price)),
                    close=Decimal(str(close_price)),
                    volume=Decimal(str(volume)),
                    interval_seconds=900,
                )
                return candle
        except Exception as e:
            logger.error(
                "fetch_latest_candle_exception",
                coin=coin,
                interval="15m",
                startTime=start_time_ms,
                endTime=end_time_ms,
                error=str(e),
                exc_info=True,
            )
            return None

    async def stream(self) -> AsyncIterator[Candle]:
        """Stream candles by polling REST API every 60 seconds.

        Yields new candles as they become available, deduplicating by timestamp.
        """
        poll_interval = 60
        last_candles: dict[str, datetime] = {}

        logger.info("starting_candle_stream", symbols=self.symbols, poll_interval=poll_interval)

        while True:
            try:
                for coin in self.symbols:
                    candle = await self.fetch_latest_candle(coin)

                    if candle:
                        last_seen = last_candles.get(coin)
                        if last_seen is None or candle.timestamp > last_seen:
                            last_candles[coin] = candle.timestamp
                            yield candle
                            logger.debug("yielded_candle", coin=coin, timestamp=candle.timestamp.isoformat())

                    await asyncio.sleep(0.5)

                await asyncio.sleep(poll_interval)
                
            except KeyboardInterrupt:
                logger.info("stream_interrupted")
                break
            except Exception as e:
                logger.error("stream_error", error=str(e), exc_info=True)
                # Wait before retrying
                await asyncio.sleep(poll_interval)

    async def fetch_candles(
        self, coin: str, start_time: datetime, end_time: Optional[datetime] = None, interval: str = "15m"
    ) -> list[Candle]:
        """Fetch historical candles for a time range."""
        start_time_ms = int(start_time.timestamp() * 1000)
        end_time_ms = int((end_time or datetime.utcnow()).timestamp() * 1000)
        
        try:
            url = f"{self.rest_url}/info"
            payload = {
                "type": "candleSnapshot",
                "req": {
                    "coin": coin.upper(),
                    "interval": interval,
                    "startTime": start_time_ms,
                    "endTime": end_time_ms,
                },
            }
            
            async with httpx.AsyncClient(timeout=30.0) as client:
                response = await client.post(
                    url,
                    json=payload,
                    headers={"Content-Type": "application/json"},
                )
                
                if response.status_code != 200:
                    response_text = response.text[:500]
                    logger.error(
                        "fetch_candles_failed",
                        coin=coin,
                        interval=interval,
                        startTime=start_time_ms,
                        endTime=end_time_ms,
                        http_status=response.status_code,
                        response_body=response_text,
                    )
                    return []
                
                data = response.json()
                
                # Hyperliquid returns array of candles directly
                candles_data = data if isinstance(data, list) else data.get("data", [])
                
                # Helper function to extract timestamp from candle dict
                def get_timestamp_ms(candle_dict):
                    """Extract timestamp in milliseconds with fallback keys."""
                    return (
                        candle_dict.get("t") or
                        candle_dict.get("time") or
                        candle_dict.get("timestamp") or
                        None
                    )
                
                candles = []
                for item in candles_data:
                    # Extract timestamp with fallback
                    ts_ms = get_timestamp_ms(item)
                    if ts_ms is None:
                        logger.warn("skipping_candle_no_timestamp", coin=coin, keys=list(item.keys()))
                        continue
                    
                    timestamp = datetime.fromtimestamp(ts_ms / 1000)
                    
                    # Extract OHLCV with fallbacks
                    open_price = item.get("o") or item.get("open")
                    high_price = item.get("h") or item.get("high")
                    low_price = item.get("l") or item.get("low")
                    close_price = item.get("c") or item.get("close")
                    volume = item.get("v") or item.get("volume") or 0
                    
                    if open_price is None or high_price is None or low_price is None or close_price is None:
                        logger.warn("skipping_candle_incomplete_ohlc", coin=coin, keys=list(item.keys()))
                        continue
                    
                    candle = Candle(
                        symbol=coin.upper(),
                        timestamp=timestamp,
                        open=Decimal(str(open_price)),
                        high=Decimal(str(high_price)),
                        low=Decimal(str(low_price)),
                        close=Decimal(str(close_price)),
                        volume=Decimal(str(volume)),
                        interval_seconds=900,  # 15m
                    )
                    candles.append(candle)

                candles.sort(key=lambda c: c.timestamp)
                logger.info("fetched_candles", coin=coin, count=len(candles), interval=interval)
                return candles
        except Exception as e:
            logger.error(
                "fetch_candles_exception",
                coin=coin,
                interval=interval,
                startTime=start_time_ms,
                endTime=end_time_ms,
                error=str(e),
                exc_info=True,
            )
            return []

    async def backfill(
        self, coin: str, last_timestamp: datetime, interval: str = "15m"
    ) -> list[Candle]:
        """Backfill missing candles after last_timestamp."""
        end_time = datetime.utcnow()
        candles = await self.fetch_candles(coin, last_timestamp, end_time, interval)
        filtered = [c for c in candles if c.timestamp > last_timestamp]
        return sorted(filtered, key=lambda c: c.timestamp)

    async def close(self) -> None:
        """Cleanup (placeholder)."""
        pass

