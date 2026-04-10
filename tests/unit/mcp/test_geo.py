import pytest
from unittest.mock import patch, MagicMock
from src.utils.geo import validate_and_geocode_address


@pytest.mark.unit
class TestValidateAndGeocodeAddress:
    def test_short_address_returns_false(self):
        is_valid, data = validate_and_geocode_address("ab")
        assert is_valid is False
        assert data is None

    def test_empty_address_returns_false(self):
        is_valid, data = validate_and_geocode_address("")
        assert is_valid is False
        assert data is None

    def test_none_address_returns_false(self):
        is_valid, data = validate_and_geocode_address(None)
        assert is_valid is False
        assert data is None

    @patch("src.utils.geo.requests.get")
    def test_valid_address(self, mock_get, geocode_response_ok):
        mock_response = MagicMock()
        mock_response.json.return_value = geocode_response_ok
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        is_valid, data = validate_and_geocode_address("10 Boulevard Heurteloup 37000 Tours")
        assert is_valid is True
        assert data["city"] == "Tours"
        assert data["citycode"] == "37261"
        assert data["latitude"] == 47.3941
        assert data["longitude"] == 0.6848
        assert data["score"] >= 0.5

    @patch("src.utils.geo.requests.get")
    def test_no_features_returns_false(self, mock_get, geocode_response_empty):
        mock_response = MagicMock()
        mock_response.json.return_value = geocode_response_empty
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        is_valid, data = validate_and_geocode_address("adresse introuvable xyz")
        assert is_valid is False
        assert data is None

    @patch("src.utils.geo.requests.get")
    def test_low_score_returns_invalid(self, mock_get):
        mock_response = MagicMock()
        mock_response.json.return_value = {
            "features": [{
                "geometry": {"coordinates": [0.68, 47.39]},
                "properties": {
                    "label": "Tours", "postcode": "37000", "city": "Tours",
                    "citycode": "37261", "type": "municipality", "score": 0.3
                },
            }]
        }
        mock_response.raise_for_status = MagicMock()
        mock_get.return_value = mock_response

        is_valid, data = validate_and_geocode_address("Tours")
        assert is_valid is False
        assert data is not None
        assert data["score"] < 0.5

    @patch("src.utils.geo.requests.get")
    def test_network_error_returns_false(self, mock_get):
        mock_get.side_effect = ConnectionError("Network unreachable")
        is_valid, data = validate_and_geocode_address("10 Boulevard Heurteloup 37000 Tours")
        assert is_valid is False
        assert data is None
