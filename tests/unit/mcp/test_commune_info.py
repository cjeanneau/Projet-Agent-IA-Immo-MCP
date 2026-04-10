import pytest
from unittest.mock import MagicMock
import pandas as pd
from src.mcp.tools.commune_info import get_commune_info


@pytest.fixture
def mock_con_with_data():
    """Mock DuckDB connection returning one row."""
    con = MagicMock()
    df = pd.DataFrame([{
        "col0": "37261",
        "col1": "Tours",
        "col2": 45,
        "col3": 120,
        "col4": 80,
        "col5": 60,
        "col6": 15,
        "col7": 200,
        "col8": 10,
    }])
    con.execute.return_value.df.return_value = df
    return con


@pytest.fixture
def mock_con_empty():
    """Mock DuckDB connection returning no rows."""
    con = MagicMock()
    df = pd.DataFrame(columns=["c0", "c1", "c2", "c3", "c4", "c5", "c6", "c7", "c8"])
    con.execute.return_value.df.return_value = df
    return con


@pytest.mark.unit
class TestGetCommuneInfo:
    def test_returns_commune_data(self, mock_con_with_data):
        result = get_commune_info(mock_con_with_data, "37261")
        assert result["code_insee"] == "37261"
        assert result["nom_commune"] == "Tours"
        assert "nombre_equipements_commerce" in result

    def test_empty_result_returns_error(self, mock_con_empty):
        result = get_commune_info(mock_con_empty, "99999")
        assert "error" in result

    def test_query_uses_code_insee(self, mock_con_with_data):
        get_commune_info(mock_con_with_data, "75101")
        query = mock_con_with_data.execute.call_args[0][0]
        assert "75101" in query
