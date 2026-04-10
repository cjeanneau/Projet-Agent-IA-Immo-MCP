import pytest
import numpy as np
import pandas as pd
from unittest.mock import patch, MagicMock
from src.inference.model import (
    normalize_street_type,
    model_predict,
    get_estimation,
    get_model,
    AddressNotFoundError,
)


@pytest.mark.unit
class TestNormalizeStreetType:
    @pytest.mark.parametrize("word,expected", [
        ("rue", "RUE"),
        ("Rue", "RUE"),
        ("avenue", "AV"),
        ("Avenue", "AV"),
        ("boulevard", "BD"),
        ("Boulevard", "BD"),
        ("chemin", "CHE"),
        ("impasse", "IMP"),
        ("place", "PL"),
        ("résidence", "RES"),
        ("residence", "RES"),
        ("route", "RTE"),
        ("allée", "ALL"),
        ("allee", "ALL"),
    ])
    def test_known_types(self, word, expected):
        assert normalize_street_type(word) == expected

    def test_unknown_type_returns_nan(self):
        assert normalize_street_type("passage") == "NAN"
        assert normalize_street_type("") == "NAN"

    def test_whitespace_is_stripped(self):
        assert normalize_street_type("  rue  ") == "RUE"


@pytest.mark.unit
class TestModelPredict:
    def test_returns_float(self):
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([np.log(200000)])

        model_input = {
            "Type local": ["Maison"],
            "latitude": [47.39],
            "longitude": [0.68],
            "Surface habitable": [100.0],
            "Nombre pieces principales": [4],
            "Surface terrain": [200.0],
            "Type de voie": ["BD"],
            "densite": [1200],
        }

        result = model_predict(mock_model, model_input)
        assert isinstance(result, float)
        assert abs(result - 200000) < 1

    def test_model_receives_dataframe(self):
        mock_model = MagicMock()
        mock_model.predict.return_value = np.array([12.0])

        model_input = {"col": ["val"]}
        model_predict(mock_model, model_input)

        call_args = mock_model.predict.call_args[0][0]
        assert isinstance(call_args, pd.DataFrame)


@pytest.mark.unit
class TestGetModel:
    @patch("src.inference.model.load_pickle")
    def test_delegates_to_load_pickle(self, mock_load):
        mock_load.return_value = "fake_model"
        result = get_model("/fake/path.pkl")
        mock_load.assert_called_once_with("/fake/path.pkl")
        assert result == "fake_model"


@pytest.mark.unit
class TestGetEstimation:
    @patch("src.inference.model.validate_and_geocode_address")
    def test_invalid_address_raises(self, mock_geo):
        mock_geo.return_value = (False, None)
        with pytest.raises(AddressNotFoundError):
            get_estimation(MagicMock(), "xyz", "maison", 100, 200, 4)

    @patch("src.inference.model.model_predict", return_value=250000.0)
    @patch("src.inference.model.validate_and_geocode_address")
    def test_valid_estimation(self, mock_geo, mock_predict):
        mock_geo.return_value = (True, {
            "address": "10 Bd Heurteloup 37000 Tours",
            "latitude": 47.39,
            "longitude": 0.68,
            "citycode": "37261",
            "type": "housenumber",
            "score": 0.92,
        })

        result = get_estimation(MagicMock(), "10 Bd Heurteloup", "maison", 100, 200, 4)

        assert result["estimation"]["price"] == 250000
        assert result["estimation"]["price_per_m2"] == 2500
        assert result["estimation"]["confidence_interval"]["min"] == 237500.0
        assert result["estimation"]["confidence_interval"]["max"] == 262500.0
        assert result["estimation"]["confidence_level"] == "high"
        assert result["coordinates"]["commune"] == "37261"

    @patch("src.inference.model.model_predict", return_value=150000.0)
    @patch("src.inference.model.validate_and_geocode_address")
    def test_medium_confidence_when_not_housenumber(self, mock_geo, mock_predict):
        mock_geo.return_value = (True, {
            "address": "Tours",
            "latitude": 47.39,
            "longitude": 0.68,
            "citycode": "37261",
            "type": "municipality",
            "score": 0.6,
        })

        result = get_estimation(MagicMock(), "Tours", "appartement", 60, 0, 3)
        assert result["estimation"]["confidence_level"] == "medium"
