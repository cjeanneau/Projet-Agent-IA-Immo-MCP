import pytest
import aiohttp
from unittest.mock import AsyncMock, MagicMock, patch
from src.mcp.tools.geocoding import geocoding


@pytest.mark.integration
class TestGeocodingClientError:
    @patch("src.mcp.tools.geocoding.get_session")
    async def test_client_error_returns_error_dict(self, mock_get_session):
        """When aiohttp raises ClientError, geocoding should catch and return error."""
        mock_session = MagicMock()
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(side_effect=aiohttp.ClientError("connection failed"))
        ctx.__aexit__ = AsyncMock(return_value=False)
        mock_session.get.return_value = ctx
        mock_get_session.return_value = mock_session

        result = await geocoding("10 Boulevard Heurteloup 37000 Tours")
        assert "error" in result
        assert "indisponible" in result["error"]
