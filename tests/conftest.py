import pytest


@pytest.fixture
def geocode_response_ok():
    """Successful geocoding API response."""
    return {
        "features": [
            {
                "geometry": {"coordinates": [0.6848, 47.3941]},
                "properties": {
                    "label": "10 Boulevard Heurteloup 37000 Tours",
                    "postcode": "37000",
                    "city": "Tours",
                    "citycode": "37261",
                    "type": "housenumber",
                    "score": 0.92,
                    "street": "Boulevard Heurteloup",
                },
            }
        ]
    }


@pytest.fixture
def geocode_response_empty():
    """Empty geocoding API response."""
    return {"features": []}


@pytest.fixture
def cerema_page_response():
    """Single page response from Cerema DVF API."""
    return {
        "count": 2,
        "features": [
            {
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
            },
            {
                "geometry": {
                    "type": "Polygon",
                    "coordinates": [[[0.70, 47.41], [0.71, 47.41], [0.71, 47.42], [0.70, 47.42], [0.70, 47.41]]],
                },
                "properties": {
                    "datemut": "2025-01-10",
                    "libtypbien": "Appartement",
                    "codtypbien": "12",
                    "sbati": 45.0,
                    "sterr": 0,
                    "valeurfonc": 120000,
                    "libnatmut": "Vente",
                },
            },
        ],
    }
