import pytest
import asyncio
from unittest.mock import AsyncMock, MagicMock, patch
from src.mcp.tools.list_transactions import (
    get_session,
    close_session,
    get_recent_transactions,
    _fetch_page,
    _fetch_all_pages,
    _session,
)


@pytest.fixture(autouse=True)
async def reset_session():
    """Reset the global session before each test."""
    import src.mcp.tools.list_transactions as mod
    mod._session = None
    yield
    if mod._session and not mod._session.closed:
        await mod._session.close()
    mod._session = None


@pytest.mark.integration
class TestGetSession:
    async def test_creates_session(self):
        session = await get_session()
        assert session is not None
        assert not session.closed
        await close_session()

    async def test_reuses_session(self):
        s1 = await get_session()
        s2 = await get_session()
        assert s1 is s2
        await close_session()

    async def test_recreates_after_close(self):
        s1 = await get_session()
        await close_session()
        s2 = await get_session()
        assert s1 is not s2
        await close_session()


@pytest.mark.integration
class TestCloseSession:
    async def test_close_when_open(self):
        await get_session()
        await close_session()
        import src.mcp.tools.list_transactions as mod
        assert mod._session is None

    async def test_close_when_already_none(self):
        await close_session()  # should not raise


@pytest.mark.integration
class TestFetchPage:
    @patch("src.mcp.tools.list_transactions.get_session")
    async def test_fetch_page_returns_features(self, mock_get_session):
        features = [{"properties": {"datemut": "2025-01-01"}}]
        mock_response = MagicMock()
        mock_response.raise_for_status = MagicMock()
        mock_response.json = AsyncMock(return_value={"features": features})

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=mock_response)
        ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get.return_value = ctx
        mock_get_session.return_value = mock_session

        result = await _fetch_page("http://test.com", {"code_insee": "37261"}, 2)
        assert result == features


@pytest.mark.integration
class TestFetchAllPages:
    @patch("src.mcp.tools.list_transactions.cache")
    @patch("src.mcp.tools.list_transactions.get_session")
    async def test_single_page(self, mock_get_session, mock_cache):
        mock_cache.get.return_value = None

        features = [
            {"geometry": {"type": "Point", "coordinates": [0.68, 47.39]},
             "properties": {"datemut": "2025-03-15", "libnatmut": "Vente", "codtypbien": "12"}}
        ]
        first_response = MagicMock()
        first_response.raise_for_status = MagicMock()
        first_response.json = AsyncMock(return_value={"count": 1, "features": features})

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=first_response)
        ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get.return_value = ctx
        mock_get_session.return_value = mock_session

        result = await _fetch_all_pages("37261", "12")
        assert len(result) == 1
        mock_cache.set.assert_called_once()

    @patch("src.mcp.tools.list_transactions.cache")
    async def test_cache_hit(self, mock_cache):
        cached_data = [{"properties": {"datemut": "2025-01-01"}}]
        mock_cache.get.return_value = cached_data

        result = await _fetch_all_pages("37261", "12")
        assert result == cached_data

    @patch("src.mcp.tools.list_transactions._fetch_page", new_callable=AsyncMock)
    @patch("src.mcp.tools.list_transactions.cache")
    @patch("src.mcp.tools.list_transactions.get_session")
    async def test_multi_page(self, mock_get_session, mock_cache, mock_fetch_page):
        mock_cache.get.return_value = None

        page1_features = [{"p": i} for i in range(100)]
        first_response = MagicMock()
        first_response.raise_for_status = MagicMock()
        first_response.json = AsyncMock(return_value={"count": 150, "features": page1_features})

        ctx = MagicMock()
        ctx.__aenter__ = AsyncMock(return_value=first_response)
        ctx.__aexit__ = AsyncMock(return_value=False)

        mock_session = MagicMock()
        mock_session.get.return_value = ctx
        mock_get_session.return_value = mock_session

        page2_features = [{"p": i} for i in range(100, 150)]
        mock_fetch_page.return_value = page2_features

        result = await _fetch_all_pages("37261", "12")
        assert len(result) == 150
        mock_fetch_page.assert_called_once()


@pytest.mark.integration
class TestGetRecentTransactions:
    @patch("src.mcp.tools.list_transactions._fetch_all_pages", new_callable=AsyncMock)
    async def test_filters_and_sorts(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                "properties": {
                    "datemut": "2025-01-10", "libtypbien": "Appartement",
                    "codtypbien": "12", "sbati": 45, "sterr": 0,
                    "valeurfonc": 120000, "libnatmut": "Vente",
                },
            },
            {
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                "properties": {
                    "datemut": "2025-03-15", "libtypbien": "Appartement",
                    "codtypbien": "12", "sbati": 65, "sterr": 0,
                    "valeurfonc": 185000, "libnatmut": "Vente",
                },
            },
            {
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                "properties": {
                    "datemut": "2025-02-01", "libtypbien": "Terrain",
                    "codtypbien": "23", "sbati": 0, "sterr": 500,
                    "valeurfonc": 50000, "libnatmut": "Vente",
                },
            },
        ]

        result = await get_recent_transactions("37261", "appartement", top_n=10)
        # Terrain should be filtered out
        assert len(result) == 2
        # Sorted by date descending
        assert result[0]["date_mutation"] == "2025-03-15"
        assert result[1]["date_mutation"] == "2025-01-10"

    @patch("src.mcp.tools.list_transactions._fetch_all_pages", new_callable=AsyncMock)
    async def test_top_n_limit(self, mock_fetch):
        mock_fetch.return_value = [
            {
                "geometry": {"type": "Polygon", "coordinates": [[[0, 0], [1, 0], [1, 1], [0, 1], [0, 0]]]},
                "properties": {
                    "datemut": f"2025-0{i+1}-01", "libtypbien": "Maison",
                    "codtypbien": "111", "sbati": 100, "sterr": 300,
                    "valeurfonc": 200000 + i * 10000, "libnatmut": "Vente",
                },
            }
            for i in range(5)
        ]

        result = await get_recent_transactions("37261", "maison", top_n=2)
        assert len(result) == 2

    @patch("src.mcp.tools.list_transactions._fetch_all_pages", new_callable=AsyncMock)
    async def test_maison_maps_to_11(self, mock_fetch):
        mock_fetch.return_value = []
        await get_recent_transactions("37261", "maison")
        mock_fetch.assert_called_once_with("37261", "11")

    @patch("src.mcp.tools.list_transactions._fetch_all_pages", new_callable=AsyncMock)
    async def test_appartement_maps_to_12(self, mock_fetch):
        mock_fetch.return_value = []
        await get_recent_transactions("37261", "appartement")
        mock_fetch.assert_called_once_with("37261", "12")
