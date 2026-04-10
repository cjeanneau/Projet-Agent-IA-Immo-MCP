import pytest
from src.mcp.tools.list_transactions import (
    extract_centroid,
    filter_transaction,
)


@pytest.mark.unit
class TestExtractCentroid:
    def test_polygon_centroid(self):
        geometry = {
            "type": "Polygon",
            "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
        }
        result = extract_centroid(geometry)
        assert result is not None
        lat, lon = result
        assert abs(lat - 0.5) < 0.01
        assert abs(lon - 0.5) < 0.01

    def test_invalid_geometry_returns_none(self):
        assert extract_centroid({}) is None
        assert extract_centroid({"type": "Invalid"}) is None


@pytest.mark.unit
class TestFilterTransaction:
    def test_valid_vente_appartement(self):
        feature = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0.68, 47.39], [0.69, 47.39], [0.69, 47.40], [0.68, 47.40], [0.68, 47.39]]],
            },
            "properties": {
                "datemut": "2025-03-15",
                "libtypbien": "Appartement",
                "codtypbien": "12",
                "sbati": 65.0,
                "sterr": 0,
                "valeurfonc": 185000,
                "libnatmut": "Vente",
            },
        }
        result = filter_transaction(feature)
        assert result is not None
        assert result["prix_euros"] == 185000
        assert result["surface_bati_m2"] == 65.0
        assert result["date_mutation"] == "2025-03-15"
        assert result["latitude"] is not None
        assert result["longitude"] is not None

    def test_valid_vente_maison(self):
        feature = {
            "geometry": {
                "type": "Polygon",
                "coordinates": [[[0.0, 0.0], [1.0, 0.0], [1.0, 1.0], [0.0, 1.0], [0.0, 0.0]]],
            },
            "properties": {
                "datemut": "2025-01-01",
                "libtypbien": "Maison",
                "codtypbien": "111",
                "sbati": 120.0,
                "sterr": 500,
                "valeurfonc": 350000,
                "libnatmut": "Vente",
            },
        }
        result = filter_transaction(feature)
        assert result is not None
        assert result["type_bien"] == "Maison"

    def test_non_vente_returns_none(self):
        feature = {
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "datemut": "2025-01-01",
                "libtypbien": "Appartement",
                "codtypbien": "12",
                "sbati": 50, "sterr": 0, "valeurfonc": 100000,
                "libnatmut": "Échange",
            },
        }
        assert filter_transaction(feature) is None

    def test_wrong_type_bien_returns_none(self):
        feature = {
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "datemut": "2025-01-01",
                "libtypbien": "Terrain",
                "codtypbien": "23",
                "sbati": 0, "sterr": 1000, "valeurfonc": 50000,
                "libnatmut": "Vente",
            },
        }
        assert filter_transaction(feature) is None

    def test_missing_codtypbien_returns_none(self):
        feature = {
            "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
            "properties": {
                "datemut": "2025-01-01",
                "libtypbien": "Autre",
                "sbati": 0, "sterr": 0, "valeurfonc": 0,
                "libnatmut": "Vente",
            },
        }
        assert filter_transaction(feature) is None
