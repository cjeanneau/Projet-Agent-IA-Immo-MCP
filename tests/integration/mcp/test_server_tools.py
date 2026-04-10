import pytest
import duckdb
from unittest.mock import AsyncMock, MagicMock, patch
from src.mcp.serverMCP import (
    geocoding_tools,
    commune_info_tools,
    recent_transactions_tools,
    estimation_tools,
    TypeBien,
)


@pytest.mark.integration
class TestGeocodingTools:
    @patch("src.mcp.serverMCP.geocoding", new_callable=AsyncMock)
    async def test_valid_address(self, mock_geocoding):
        mock_geocoding.return_value = {
            "adresse": "10 Bd Heurteloup 37000 Tours",
            "code_insee": "37261",
            "latitude": 47.39,
            "longitude": 0.68,
        }
        result = await geocoding_tools("10 Boulevard Heurteloup 37000 Tours")
        assert result["code_insee"] == "37261"

    async def test_empty_address(self):
        result = await geocoding_tools("")
        assert "error" in result

    async def test_short_address(self):
        result = await geocoding_tools("a")
        assert "error" in result

    @patch("src.mcp.serverMCP.geocoding", new_callable=AsyncMock)
    async def test_unexpected_exception(self, mock_geocoding):
        mock_geocoding.side_effect = ValueError("unexpected")
        result = await geocoding_tools("10 Bd Heurteloup")
        assert "error" in result
        assert "ValueError" in result["error"]


@pytest.mark.integration
class TestCommuneInfoTools:
    async def test_invalid_code_insee_letters(self):
        result = await commune_info_tools("abcde")
        assert "error" in result

    async def test_invalid_code_insee_too_short(self):
        result = await commune_info_tools("123")
        assert "error" in result

    async def test_empty_code_insee(self):
        result = await commune_info_tools("")
        assert "error" in result

    @patch("src.mcp.serverMCP.get_commune_info")
    @patch("src.mcp.serverMCP.con")
    async def test_valid_code_returns_data(self, mock_con, mock_get_info):
        mock_get_info.return_value = {"code_insee": "37261", "nom_commune": "Tours"}
        result = await commune_info_tools("37261")
        assert result["nom_commune"] == "Tours"

    @patch("src.mcp.serverMCP.get_commune_info")
    @patch("src.mcp.serverMCP.con")
    async def test_empty_result(self, mock_con, mock_get_info):
        mock_get_info.return_value = {}
        result = await commune_info_tools("99999")
        assert "error" in result

    @patch("src.mcp.serverMCP.get_commune_info")
    @patch("src.mcp.serverMCP.con")
    async def test_duckdb_error(self, mock_con, mock_get_info):
        mock_get_info.side_effect = duckdb.Error("DB error")
        result = await commune_info_tools("37261")
        assert "error" in result
        assert "base de données" in result["error"]

    @patch("src.mcp.serverMCP.get_commune_info")
    @patch("src.mcp.serverMCP.con")
    async def test_unexpected_exception(self, mock_con, mock_get_info):
        mock_get_info.side_effect = RuntimeError("unexpected")
        result = await commune_info_tools("37261")
        assert "error" in result
        assert "RuntimeError" in result["error"]


@pytest.mark.integration
class TestRecentTransactionsTools:
    async def test_invalid_code_insee(self):
        result = await recent_transactions_tools("abc", TypeBien.maison)
        assert "error" in result

    async def test_empty_code_insee(self):
        result = await recent_transactions_tools("", TypeBien.appartement)
        assert "error" in result

    @patch("src.mcp.serverMCP.get_recent_transactions", new_callable=AsyncMock)
    async def test_returns_transactions(self, mock_get):
        mock_get.return_value = [
            {"date_mutation": "2025-03-15", "prix_euros": 185000},
            {"date_mutation": "2025-01-10", "prix_euros": 120000},
        ]
        result = await recent_transactions_tools("37261", TypeBien.appartement, n=5)
        assert "transactions" in result
        assert len(result["transactions"]) == 2

    @patch("src.mcp.serverMCP.get_recent_transactions", new_callable=AsyncMock)
    async def test_no_transactions(self, mock_get):
        mock_get.return_value = []
        result = await recent_transactions_tools("37261", TypeBien.maison)
        assert "error" in result

    @patch("src.mcp.serverMCP.get_recent_transactions", new_callable=AsyncMock)
    async def test_n_clamped(self, mock_get):
        mock_get.return_value = [{"date_mutation": "2025-01-01", "prix_euros": 100000}]
        await recent_transactions_tools("37261", TypeBien.maison, n=100)
        _, kwargs = mock_get.call_args
        assert kwargs["top_n"] <= 50

    @patch("src.mcp.serverMCP.get_recent_transactions", new_callable=AsyncMock)
    async def test_unexpected_exception(self, mock_get):
        mock_get.side_effect = ValueError("unexpected")
        result = await recent_transactions_tools("37261", TypeBien.maison)
        assert "error" in result


@pytest.mark.integration
class TestEstimationTools:
    async def test_zero_surface_returns_error(self):
        result = await estimation_tools("10 Bd Heurteloup", "maison", 0, 200, 4)
        assert "error" in result
        assert "surface" in result["error"].lower()

    async def test_zero_pieces_returns_error(self):
        result = await estimation_tools("10 Bd Heurteloup", "maison", 100, 200, 0)
        assert "error" in result
        assert "pièces" in result["error"].lower()

    async def test_empty_address_returns_error(self):
        result = await estimation_tools("", "maison", 100, 200, 4)
        assert "error" in result

    @patch("src.mcp.serverMCP.estimate_price")
    async def test_valid_estimation(self, mock_estimate):
        mock_estimate.return_value = {"estimation": {"price": 250000}}
        result = await estimation_tools("10 Bd Heurteloup 37000 Tours", "maison", 100, 200, 4)
        assert result["estimation"]["price"] == 250000

    @patch("src.mcp.serverMCP.estimate_price")
    async def test_estimation_exception(self, mock_estimate):
        mock_estimate.side_effect = RuntimeError("model failed")
        result = await estimation_tools("10 Bd Heurteloup", "maison", 100, 200, 4)
        assert "error" in result
        assert "RuntimeError" in result["error"]
