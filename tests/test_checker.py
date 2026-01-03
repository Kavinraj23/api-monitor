import json
from unittest.mock import AsyncMock, MagicMock, patch

import pytest

from app.checker import run_check
from app.models import APICheck


def _mock_async_client(mock_response):
    """Helper to create a properly mocked AsyncClient context manager."""
    mock_client = AsyncMock()
    mock_client.request = AsyncMock(return_value=mock_response)
    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)
    return mock_client_instance


@pytest.mark.asyncio
async def test_run_check_pass():
    """Happy path: status 200, all fields present, latency under threshold."""
    check = APICheck(
        method="GET",
        url="http://example.com/api",
        required_fields=["status", "data.id"],
        expected_status_code=200,
        latency_threshold_ms=1000,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok", "data": {"id": 123}}

    with patch("app.checker.httpx.AsyncClient", return_value=_mock_async_client(mock_response)):
        result = await run_check(check)

        assert result["status"] == "PASS"
        assert result["missing_fields"] == []
        assert result["status_code"] == 200
        assert result["error"] is None


@pytest.mark.asyncio
async def test_run_check_fail_bad_status():
    """Fail: wrong status code."""
    check = APICheck(
        method="GET",
        url="http://example.com/api",
        required_fields=[],
        expected_status_code=200,
    )

    mock_response = MagicMock()
    mock_response.status_code = 500
    mock_response.json.return_value = {}

    with patch("app.checker.httpx.AsyncClient", return_value=_mock_async_client(mock_response)):
        result = await run_check(check)

        assert result["status"] == "FAIL"
        assert result["status_code"] == 500


@pytest.mark.asyncio
async def test_run_check_fail_missing_fields():
    """Fail: required field missing."""
    check = APICheck(
        method="GET",
        url="http://example.com/api",
        required_fields=["status", "missing_field"],
        expected_status_code=200,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {"status": "ok"}

    with patch("app.checker.httpx.AsyncClient", return_value=_mock_async_client(mock_response)):
        result = await run_check(check)

        assert result["status"] == "FAIL"
        assert "missing_field" in result["missing_fields"]


@pytest.mark.asyncio
async def test_run_check_fail_latency_threshold():
    """Fail: latency exceeds threshold."""
    check = APICheck(
        method="GET",
        url="http://example.com/api",
        required_fields=[],
        expected_status_code=200,
        latency_threshold_ms=100,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.return_value = {}

    with patch("app.checker.httpx.AsyncClient", return_value=_mock_async_client(mock_response)):
        with patch("app.checker.time.perf_counter") as mock_time:
            # Simulate 500ms latency
            mock_time.side_effect = [0.0, 0.5]

            result = await run_check(check)

            assert result["status"] == "FAIL"
            assert result["latency_ms"] > 100


@pytest.mark.asyncio
async def test_run_check_fail_invalid_json():
    """Fail: response is not valid JSON."""
    check = APICheck(
        method="GET",
        url="http://example.com/api",
        required_fields=[],
        expected_status_code=200,
    )

    mock_response = MagicMock()
    mock_response.status_code = 200
    mock_response.json.side_effect = json.JSONDecodeError("Invalid JSON", "", 0)

    with patch("app.checker.httpx.AsyncClient", return_value=_mock_async_client(mock_response)):
        result = await run_check(check)

        assert result["status"] == "FAIL"
        assert "not valid JSON" in result["error"]


@pytest.mark.asyncio
async def test_run_check_fail_request_error():
    """Fail: HTTP request fails (network error, timeout, etc.)."""
    check = APICheck(
        method="GET",
        url="http://example.com/api",
        required_fields=[],
        expected_status_code=200,
    )

    import httpx

    mock_client = AsyncMock()
    mock_client.request = AsyncMock(side_effect=httpx.RequestError("Connection failed"))
    mock_client_instance = AsyncMock()
    mock_client_instance.__aenter__ = AsyncMock(return_value=mock_client)
    mock_client_instance.__aexit__ = AsyncMock(return_value=None)

    with patch("app.checker.httpx.AsyncClient", return_value=mock_client_instance):
        result = await run_check(check)

        assert result["status"] == "FAIL"
        assert "after" in result["error"]
        assert "attempts" in result["error"]
