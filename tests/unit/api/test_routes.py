import pytest
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def mock_agent():
    agent = AsyncMock()
    agent.ainvoke = AsyncMock(return_value={
        "messages": [MagicMock(content="Bonjour, je suis votre agent immobilier.")]
    })
    return agent


@pytest.fixture
def app_with_agent(mock_agent):
    """Create a FastAPI app with a pre-configured mock agent."""
    with patch("src.app.routes.create_client", new_callable=AsyncMock), \
         patch("src.app.routes.create_agent", new_callable=AsyncMock) as mock_create:
        mock_create.return_value = mock_agent

        from src.app.main import app
        app.state.agent = mock_agent
        app.state.mcp_client = MagicMock()
        app.state.mcp_tools = {}
        import asyncio
        app.state._mcp_lock = asyncio.Lock()
        yield app


@pytest.fixture
def client(app_with_agent):
    return TestClient(app_with_agent)


@pytest.mark.unit
class TestHealthcheck:
    def test_healthcheck_returns_ok(self, client):
        response = client.get("/healthcheck")
        assert response.status_code == 200
        assert response.json() == {"status": "OK"}


@pytest.mark.unit
class TestHome:
    def test_home_returns_html(self, client):
        response = client.get("/")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]


@pytest.mark.unit
class TestChatbot:
    def test_chatbot_page_returns_html(self, client):
        response = client.get("/chatbot")
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_chat_returns_message(self, client, mock_agent):
        response = client.post("/chat", json={
            "messages": [{"role": "user", "content": "Bonjour"}]
        })
        assert response.status_code == 200
        data = response.json()
        assert "message" in data
        mock_agent.ainvoke.assert_called_once()

    def test_chat_with_empty_messages(self, client, mock_agent):
        response = client.post("/chat", json={"messages": []})
        assert response.status_code == 200
        mock_agent.ainvoke.assert_called_once()

    def test_chat_invalid_body(self, client):
        response = client.post("/chat", json={"wrong": "field"})
        assert response.status_code == 422


@pytest.mark.unit
class TestPredict:
    def test_predict_with_mcp_tool(self, client, app_with_agent):
        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(return_value=[{
            "text": '{"input":{"type":"maison","address":"10 Bd Heurteloup 37000 Tours","surface_habitable":100,"nombre_pieces":4,"surface_terrain":200},"coordinates":{"latitude":47.39,"longitude":0.68,"commune":"37261"},"estimation":{"price":250000,"price_per_m2":2500,"confidence_interval":{"min":237500,"max":262500},"confidence_level":"high"},"metadata":{"address_score":0.92,"address_type":"housenumber"}}'
        }])
        app_with_agent.state.mcp_tools = {"estimation_tools": mock_tool}

        response = client.post("/predict", data={
            "type_local": "maison",
            "address": "10 Boulevard Heurteloup 37000 Tours",
            "surface_habitable": 100,
            "nombre_pieces": 4,
        })
        assert response.status_code == 200
        assert "text/html" in response.headers["content-type"]

    def test_predict_missing_required_field(self, client):
        response = client.post("/predict", data={
            "type_local": "maison",
            "surface_habitable": 100,
            "nombre_pieces": 4,
        })
        assert response.status_code == 422
