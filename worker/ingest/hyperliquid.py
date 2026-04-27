"""Hyperliquid market data client — REST + WebSocket.

Two ingestion modes, selected by `settings.ingest_mode`:

* `ws`   — subscribe to Hyperliquid's WebSocket `candle` channel for all
           configured symbols on a single connection. Auto-reconnects with
           exponential backoff. On every reconnect, REST-backfills any
           candles closed between the last seen timestamp and the new
           connection. Heartbeat timeout forces reconnect if silent.
* `poll` — legacy path: REST-poll `/info` every 60s. Kept for rollback.

REST helpers (`fetch_latest_candle`, `fetch_candles`, `backfill`) are
available regardless of mode — the WS path uses them for gap recovery.
"""
import asyncio
import json
from datetime import datetime
from decimal import Decimal
from typing import AsyncIterator, Optional

import httpx
import websockets
from websockets.exceptions import ConnectionClosed, WebSocketException

from core.logging import get_logger
from core.time import from_ms, now_ms, to_ms, utcnow
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


def _get_timestamp_ms(data: dict) -> Optional[int]:
    return data.get("t") or data.get("time") or data.get("timestamp")


def _candle_from_dict(symbol: str, data: dict, interval_seconds: int = 900) -> Optional[Candle]:
    """Parse a candle dict (REST or WS shape). Returns None on malformed input."""
    ts_ms = _get_timestamp_ms(data)
    if ts_ms is None:
        return None
    o = data.get("o") or data.get("open")
    h = data.get("h") or data.get("high")
    low_ = data.get("l") or data.get("low")
    c = data.get("c") or data.get("close")
    v = data.get("v") or data.get("volume") or 0
    if o is None or h is None or low_ is None or c is None:
        return None
    try:
        return Candle(
            symbol=symbol.upper(),
            timestamp=from_ms(int(ts_ms)),
            open=Decimal(str(o)),
            high=Decimal(str(h)),
            low=Decimal(str(low_)),
            close=Decimal(str(c)),
            volume=Decimal(str(v)),
            interval_seconds=interval_seconds,
        )
    except (ValueError, TypeError):
        return None


class HyperliquidClient:
    """Client for Hyperliquid. REST for backfill/history, WS for live stream."""

    def __init__(self):
        self.rest_url = settings.hyperliquid_rest_url
        self.ws_url = settings.hyperliquid_ws_url
        self.symbols = settings.symbol_list
        self.mode = settings.ingest_mode.lower()
        self._last_candle_ts: dict[str, datetime] = {}

    async def connect(self) -> None:
        """Log init. WS connection is lazy in `stream()`."""
        logger.info(
            "hyperliquid_client_initialized",
            symbols=self.symbols,
            mode=self.mode,
        )

    async def close(self) -> None:
        """No persistent resources to release — WS lifecycle is scoped to stream()."""
        return None

    def seed_last_seen(self, cursors: dict[str, datetime]) -> None:
        """Seed per-symbol last-seen timestamps from DB cursors.

        Called once at startup so the first WS connect can REST-backfill
        anything missed while the worker was down.
        """
        for sym, ts in cursors.items():
            if ts is not None:
                self._last_candle_ts[sym.upper()] = ts

    # ------------------------------------------------------------------ REST

    async def fetch_latest_candle(self, coin: str) -> Optional[Candle]:
        """Fetch latest candle for a coin (used by poll mode).

        Requests last 200 candles and returns the most recent one.
        """
        INTERVAL_MS = 15 * 60 * 1000
        CANDLES_BACK = 200
        end_time_ms = now_ms()
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
                response = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if response.status_code != 200:
                    logger.error(
                        "fetch_latest_candle_failed",
                        coin=coin,
                        interval="15m",
                        startTime=start_time_ms,
                        endTime=end_time_ms,
                        http_status=response.status_code,
                        response_body=response.text[:500],
                    )
                    return None

                data = response.json()
                candles_data = data if isinstance(data, list) else data.get("data", [])
                if not candles_data:
                    return None

                candles_data = sorted(candles_data, key=lambda x: _get_timestamp_ms(x) or 0)
                latest = candles_data[-1]
                candle = _candle_from_dict(coin, latest, interval_seconds=900)
                if candle is None:
                    logger.warn("skipping_candle_malformed", coin=coin, keys=list(latest.keys()))
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

    async def fetch_candles(
        self,
        coin: str,
        start_time: datetime,
        end_time: Optional[datetime] = None,
        interval: str = "15m",
    ) -> list[Candle]:
        """Fetch historical candles for a time range."""
        start_time_ms = to_ms(start_time)
        end_time_ms = to_ms(end_time) if end_time else now_ms()
        interval_seconds = _interval_to_seconds(interval)

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
                response = await client.post(url, json=payload, headers={"Content-Type": "application/json"})
                if response.status_code != 200:
                    logger.error(
                        "fetch_candles_failed",
                        coin=coin,
                        http_status=response.status_code,
                        response_body=response.text[:500],
                    )
                    return []

                data = response.json()
                items = data if isinstance(data, list) else data.get("data", [])
                candles: list[Candle] = []
                for item in items:
                    candle = _candle_from_dict(coin, item, interval_seconds=interval_seconds)
                    if candle is None:
                        logger.warn("skipping_candle_malformed", coin=coin, keys=list(item.keys()))
                        continue
                    candles.append(candle)
                candles.sort(key=lambda c: c.timestamp)
                logger.info("fetched_candles", coin=coin, count=len(candles), interval=interval)
                return candles
        except Exception as e:
            logger.error("fetch_candles_exception", coin=coin, error=str(e), exc_info=True)
            return []

    async def backfill(
        self, coin: str, last_timestamp: datetime, interval: str = "15m"
    ) -> list[Candle]:
        """Return candles strictly newer than `last_timestamp`."""
        candles = await self.fetch_candles(coin, last_timestamp, utcnow(), interval)
        return [c for c in candles if c.timestamp > last_timestamp]

    # ---------------------------------------------------------------- stream

    async def stream(self) -> AsyncIterator[Candle]:
        """Yield candles as they arrive. Dispatches on `settings.ingest_mode`."""
        if self.mode == "ws":
            async for candle in self._stream_ws():
                yield candle
        else:
            async for candle in self._stream_poll():
                yield candle

    async def _stream_poll(self) -> AsyncIterator[Candle]:
        """Legacy REST-poll stream. Kept for rollback — delete once WS is proven."""
        poll_interval = 60
        last_candles: dict[str, datetime] = dict(self._last_candle_ts)
        logger.info("starting_poll_stream", symbols=self.symbols, poll_interval=poll_interval)

        while True:
            try:
                for coin in self.symbols:
                    candle = await self.fetch_latest_candle(coin)
                    if candle:
                        last_seen = last_candles.get(coin)
                        if last_seen is None or candle.timestamp > last_seen:
                            last_candles[coin] = candle.timestamp
                            self._last_candle_ts[coin] = candle.timestamp
                            yield candle
                    await asyncio.sleep(0.5)
                await asyncio.sleep(poll_interval)
            except asyncio.CancelledError:
                raise
            except Exception as e:
                logger.error("poll_stream_error", error=str(e), exc_info=True)
                await asyncio.sleep(poll_interval)

    async def _stream_ws(self) -> AsyncIterator[Candle]:
        """WebSocket stream with reconnect + REST backfill on each reconnect.

        One socket, multi-subscription for all configured symbols. If no
        message arrives within `ws_heartbeat_timeout`, the socket is force-
        closed so the outer loop reconnects.
        """
        interval = "15m"
        interval_seconds = 900
        backoff = 1.0

        while True:
            try:
                logger.info("ws_connecting", url=self.ws_url, symbols=self.symbols)
                async with websockets.connect(
                    self.ws_url,
                    ping_interval=20,
                    ping_timeout=20,
                    close_timeout=10,
                    max_size=2**20,
                ) as ws:
                    backoff = 1.0

                    for coin in self.symbols:
                        await ws.send(
                            json.dumps(
                                {
                                    "method": "subscribe",
                                    "subscription": {
                                        "type": "candle",
                                        "coin": coin.upper(),
                                        "interval": interval,
                                    },
                                }
                            )
                        )
                    logger.info("ws_subscribed", symbols=self.symbols, interval=interval)

                    for coin in self.symbols:
                        last = self._last_candle_ts.get(coin.upper())
                        if last is None:
                            continue
                        try:
                            missed = await self.backfill(coin, last, interval)
                        except Exception as e:
                            logger.error("ws_backfill_failed", coin=coin, error=str(e))
                            continue
                        for c in missed:
                            self._last_candle_ts[c.symbol] = c.timestamp
                            yield c
                        if missed:
                            logger.info("ws_backfill_emitted", coin=coin, count=len(missed))

                    while True:
                        try:
                            raw = await asyncio.wait_for(
                                ws.recv(),
                                timeout=settings.ws_heartbeat_timeout,
                            )
                        except asyncio.TimeoutError:
                            logger.warn(
                                "ws_heartbeat_timeout",
                                timeout_seconds=settings.ws_heartbeat_timeout,
                            )
                            await ws.close()
                            break

                        try:
                            msg = json.loads(raw)
                        except json.JSONDecodeError:
                            logger.warn("ws_bad_json", raw=str(raw)[:200])
                            continue

                        if not isinstance(msg, dict):
                            continue

                        channel = msg.get("channel")
                        if channel in ("subscriptionResponse", "pong", "error"):
                            if channel == "error":
                                logger.error("ws_server_error", data=msg.get("data"))
                            continue
                        if channel != "candle":
                            logger.debug("ws_unhandled_channel", channel=channel)
                            continue

                        data = msg.get("data")
                        if not isinstance(data, dict):
                            continue

                        coin = (
                            data.get("s")
                            or data.get("coin")
                            or data.get("symbol")
                            or ""
                        ).upper()
                        if not coin:
                            continue

                        # Hyperliquid sends live updates for the in-progress
                        # candle. Only emit once the interval end has passed,
                        # or if the payload explicitly marks it closed.
                        end_ms = data.get("T") or data.get("endMs")
                        is_closed = bool(data.get("closed")) or (
                            end_ms is not None and int(end_ms) <= now_ms()
                        )
                        if not is_closed:
                            continue

                        candle = _candle_from_dict(coin, data, interval_seconds)
                        if candle is None:
                            continue

                        prev = self._last_candle_ts.get(coin)
                        if prev is not None and candle.timestamp <= prev:
                            continue
                        self._last_candle_ts[coin] = candle.timestamp
                        yield candle

            except asyncio.CancelledError:
                raise
            except (ConnectionClosed, WebSocketException, OSError) as e:
                wait = min(backoff, 60.0)
                logger.warn(
                    "ws_disconnected_reconnecting",
                    error=str(e),
                    wait_seconds=wait,
                )
                await asyncio.sleep(wait)
                backoff = min(backoff * 2, 60.0)
            except Exception as e:
                wait = min(backoff, 60.0)
                logger.error(
                    "ws_unexpected_error_reconnecting",
                    error=str(e),
                    wait_seconds=wait,
                    exc_info=True,
                )
                await asyncio.sleep(wait)
                backoff = min(backoff * 2, 60.0)


def _interval_to_seconds(interval: str) -> int:
    """Map a Hyperliquid interval string to seconds (e.g. '15m' -> 900)."""
    mapping = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "30m": 1800,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }
    return mapping.get(interval, 900)
