"""Unit tests for Hyperliquid client."""
import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from datetime import datetime
from decimal import Decimal
from worker.ingest.hyperliquid import HyperliquidClient, Candle


@pytest.mark.asyncio
async def test_fetch_latest_candle_request_body():
    """Test that fetch_latest_candle sends correct POST request body."""
    client = HyperliquidClient()
    
    with patch("worker.ingest.hyperliquid.httpx.AsyncClient") as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = [
            {
                "time": 1704067200000,  # Example timestamp
                "open": "50000",
                "high": "51000",
                "low": "49000",
                "close": "50500",
                "volume": "1000",
            }
        ]
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        result = await client.fetch_latest_candle("BTC")
        
        # Verify POST was called
        assert mock_client.post.called
        
        # Get the call arguments
        call_args = mock_client.post.call_args
        
        # Verify URL
        assert call_args[0][0] == "https://api.hyperliquid.xyz/info"
        
        # Verify headers
        assert call_args[1]["headers"]["Content-Type"] == "application/json"
        
        # Verify payload structure
        payload = call_args[1]["json"]
        assert payload["type"] == "candleSnapshot"
        assert "req" in payload
        assert payload["req"]["coin"] == "BTC"
        assert payload["req"]["interval"] == "15m"
        assert "startTime" in payload["req"]
        assert "endTime" in payload["req"]
        assert payload["req"]["endTime"] > payload["req"]["startTime"]
        
        # Verify result
        assert result is not None
        assert isinstance(result, Candle)
        assert result.symbol == "BTC"


@pytest.mark.asyncio
async def test_fetch_candles_request_body():
    """Test that fetch_candles sends correct POST request body."""
    client = HyperliquidClient()
    
    from datetime import timezone
    start_time = datetime(2024, 1, 1, 0, 0, 0)
    end_time = datetime(2024, 1, 1, 1, 0, 0)
    start_ms = int(start_time.replace(tzinfo=timezone.utc).timestamp() * 1000)
    end_ms = int(end_time.replace(tzinfo=timezone.utc).timestamp() * 1000)
    
    with patch("worker.ingest.hyperliquid.httpx.AsyncClient") as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        await client.fetch_candles("ETH", start_time, end_time, "15m")
        
        # Verify POST was called
        assert mock_client.post.called
        
        # Get the call arguments
        call_args = mock_client.post.call_args
        
        # Verify payload structure
        payload = call_args[1]["json"]
        assert payload["type"] == "candleSnapshot"
        assert payload["req"]["coin"] == "ETH"
        assert payload["req"]["interval"] == "15m"
        assert payload["req"]["startTime"] == start_ms
        assert payload["req"]["endTime"] == end_ms


@pytest.mark.asyncio
async def test_fetch_latest_candle_rolling_window():
    """Test that fetch_latest_candle uses rolling window correctly."""
    client = HyperliquidClient()
    
    with patch("worker.ingest.hyperliquid.httpx.AsyncClient") as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = []
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        await client.fetch_latest_candle("BTC")
        
        call_args = mock_client.post.call_args
        payload = call_args[1]["json"]
        
        # Verify rolling window: endTime - startTime should be ~200 * 15min
        INTERVAL_MS = 15 * 60 * 1000
        CANDLES_BACK = 200
        expected_window = CANDLES_BACK * INTERVAL_MS
        actual_window = payload["req"]["endTime"] - payload["req"]["startTime"]
        
        # Allow small tolerance for timing
        assert abs(actual_window - expected_window) < 1000  # Within 1 second


@pytest.mark.asyncio
async def test_fetch_latest_candle_error_logging():
    """Test error logging includes all required fields."""
    client = HyperliquidClient()
    
    with patch("worker.ingest.hyperliquid.httpx.AsyncClient") as mock_client_class:
        mock_response = MagicMock()
        mock_response.status_code = 404
        mock_response.text = "Not Found"
        
        mock_client = AsyncMock()
        mock_client.__aenter__.return_value = mock_client
        mock_client.__aexit__.return_value = None
        mock_client.post = AsyncMock(return_value=mock_response)
        mock_client_class.return_value = mock_client
        
        with patch("worker.ingest.hyperliquid.logger") as mock_logger:
            result = await client.fetch_latest_candle("BTC")
            
            assert result is None
            
            # Verify error was logged with all fields
            error_call = None
            for call in mock_logger.error.call_args_list:
                if call[0][0] == "fetch_latest_candle_failed":
                    error_call = call
                    break
            
            assert error_call is not None
            kwargs = error_call[1]
            assert "coin" in kwargs
            assert "interval" in kwargs
            assert "startTime" in kwargs
            assert "endTime" in kwargs
            assert "http_status" in kwargs
            assert "response_body" in kwargs

