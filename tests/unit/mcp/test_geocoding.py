import pytest
from unittest.mock import AsyncMock, patch, MagicMock
from aiohttp import ClientSession
from src.mcp.tools.geocoding import geocoding


@pytest.mark.unit
class TestGeocoding:
    async def test_short_address_raises(self):
        with pytest.raises(ValueError, match="Adresse invalide"):
            await geocoding("ab")

    async def test_empty_address_raises(self):
        with pytest.raises(ValueError, match="Adresse invalide"):
            await geocoding("")

    @patch("src.mcp.tools.geocoding.get_session")
    async def test_valid_address_returns_data(self, mock_get_session, geocode_response_ok):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=geocode_response_ok)

        # aiohttp session.get() returns a context manager (not a coroutine)
        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_response)
        ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock(spec=ClientSession)
        mock_session.get.return_value = ctx
        mock_get_session.return_value = mock_session

        result = await geocoding("10 Boulevard Heurteloup 37000 Tours")
        assert result["code_insee"] == "37261"
        assert result["latitude"] == 47.3941
        assert result["longitude"] == 0.6848
        assert "adresse" in result

    @patch("src.mcp.tools.geocoding.get_session")
    async def test_no_results_returns_error(self, mock_get_session, geocode_response_empty):
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value=geocode_response_empty)

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_response)
        ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock(spec=ClientSession)
        mock_session.get.return_value = ctx
        mock_get_session.return_value = mock_session

        result = await geocoding("adresse introuvable xyz123")
        assert "error" in result
