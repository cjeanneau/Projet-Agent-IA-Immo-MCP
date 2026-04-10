import pytest
from unittest.mock import patch, MagicMock
from src.mcp.tools.do_prediction import estimate_price


@pytest.mark.integration
class TestEstimatePrice:
    @patch("src.mcp.tools.do_prediction.get_estimation")
    @patch("src.mcp.tools.do_prediction.model")
    def test_delegates_to_get_estimation(self, mock_model, mock_get_est):
        mock_get_est.return_value = {"estimation": {"price": 250000}}
        result = estimate_price("10 Bd Heurteloup", "maison", 100, 200, 4)
        mock_get_est.assert_called_once_with(
            mock_model, "10 Bd Heurteloup", "maison", 100, 200, 4
        )
        assert result["estimation"]["price"] == 250000
