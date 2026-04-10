import pytest
from src.mcp.serverMCP import _is_retryable, TypeBien
import aiohttp
import asyncio


@pytest.mark.unit
class TestIsRetryable:
    def test_retryable_status_codes(self):
        for status in (429, 502, 503, 504):
            exc = aiohttp.ClientResponseError(
                request_info=aiohttp.RequestInfo(
                    url="http://test", method="GET", headers={}, real_url="http://test"
                ),
                history=(),
                status=status,
            )
            assert _is_retryable(exc) is True

    def test_non_retryable_status(self):
        exc = aiohttp.ClientResponseError(
            request_info=aiohttp.RequestInfo(
                url="http://test", method="GET", headers={}, real_url="http://test"
            ),
            history=(),
            status=404,
        )
        assert _is_retryable(exc) is False

    def test_connection_error_is_retryable(self):
        assert _is_retryable(ConnectionError()) is True

    def test_timeout_is_retryable(self):
        assert _is_retryable(asyncio.TimeoutError()) is True

    def test_value_error_not_retryable(self):
        assert _is_retryable(ValueError("bad")) is False


@pytest.mark.unit
class TestTypeBien:
    def test_maison_value(self):
        assert TypeBien.maison == "maison"

    def test_appartement_value(self):
        assert TypeBien.appartement == "appartement"

    def test_invalid_raises(self):
        with pytest.raises(ValueError):
            TypeBien("terrain")
