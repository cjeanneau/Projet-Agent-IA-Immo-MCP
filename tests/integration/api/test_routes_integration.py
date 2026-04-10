import pytest
import asyncio
import json
from unittest.mock import AsyncMock, MagicMock, patch
from fastapi.testclient import TestClient


@pytest.fixture
def fresh_app():
    """App with no pre-configured agent (agent=None), to test lazy init."""
    with patch("src.app.routes.create_client", new_callable=AsyncMock) as mock_client, \
         patch("src.app.routes.create_agent", new_callable=AsyncMock) as mock_create:

        mock_tool = MagicMock()
        mock_tool.name = "estimation_tools"
        mock_mcp_client = AsyncMock()
        mock_mcp_client.get_tools.return_value = [mock_tool]
        mock_client.return_value = mock_mcp_client

        mock_agent = AsyncMock()
        mock_agent.ainvoke = AsyncMock(return_value={
            "messages": [MagicMock(content="Réponse de l'agent")]
        })
        mock_agent.astream_events = MagicMock()
        mock_create.return_value = mock_agent

        from src.app.main import app
        app.state.agent = None
        app.state.mcp_client = None
        app.state.mcp_tools = None
        app.state._mcp_lock = asyncio.Lock()

        yield app, mock_agent


@pytest.fixture
def client(fresh_app):
    app, _ = fresh_app
    return TestClient(app)


@pytest.mark.integration
class TestLazyAgentInit:
    def test_chat_triggers_lazy_init(self, fresh_app):
        """First chat call should trigger lazy MCP connection."""
        app, mock_agent = fresh_app
        client = TestClient(app)
        assert app.state.agent is None

        response = client.post("/chat", json={
            "messages": [{"role": "user", "content": "Bonjour"}]
        })
        assert response.status_code == 200
        assert app.state.agent is not None

    def test_second_call_reuses_agent(self, fresh_app):
        """Second call should not re-create the agent."""
        app, mock_agent = fresh_app
        client = TestClient(app)

        client.post("/chat", json={"messages": [{"role": "user", "content": "Premier"}]})
        client.post("/chat", json={"messages": [{"role": "user", "content": "Deuxième"}]})
        assert mock_agent.ainvoke.call_count == 2


@pytest.mark.integration
class TestPredictErrors:
    def test_predict_tool_exception_returns_error_page(self, fresh_app):
        """When MCP tool raises, should render error.html with 500."""
        app, _ = fresh_app
        client = TestClient(app)

        # First trigger lazy init
        client.post("/chat", json={"messages": [{"role": "user", "content": "init"}]})

        # Now make the estimation tool raise
        mock_tool = AsyncMock()
        mock_tool.ainvoke = AsyncMock(side_effect=RuntimeError("MCP tool crashed"))
        app.state.mcp_tools = {"estimation_tools": mock_tool}

        response = client.post("/predict", data={
            "type_local": "maison",
            "address": "10 Boulevard Heurteloup 37000 Tours",
            "surface_habitable": 100,
            "nombre_pieces": 4,
        })
        assert response.status_code == 500
        assert "text/html" in response.headers["content-type"]

    def test_predict_agent_unavailable(self):
        """When MCP connection fails, predict should raise 500."""
        with patch("src.app.routes.create_client", new_callable=AsyncMock) as mock_client:
            mock_client.side_effect = ConnectionError("MCP down")

            from src.app.main import app
            app.state.agent = None
            app.state.mcp_client = None
            app.state.mcp_tools = None
            app.state._mcp_lock = asyncio.Lock()

            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/predict", data={
                "type_local": "maison",
                "address": "10 Boulevard Heurteloup",
                "surface_habitable": 100,
                "nombre_pieces": 4,
            })
            assert response.status_code == 500


@pytest.mark.integration
class TestChatStream:
    def test_stream_returns_sse(self, fresh_app):
        """Chat stream should return SSE events."""
        app, mock_agent = fresh_app
        client = TestClient(app)

        # Setup stream events
        async def fake_stream(*args, **kwargs):
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content="Bonjour")}
            }
            yield {
                "event": "on_chat_model_stream",
                "data": {"chunk": MagicMock(content=" monde")}
            }
            yield {
                "event": "on_tool_start",
                "data": {}
            }

        mock_agent.astream_events = fake_stream

        response = client.post("/chat/stream", json={
            "messages": [{"role": "user", "content": "Salut"}]
        })
        assert response.status_code == 200
        assert "text/event-stream" in response.headers["content-type"]

        lines = response.text.strip().split("\n")
        data_lines = [l for l in lines if l.startswith("data:")]
        # Should have 2 content chunks + 1 DONE
        assert len(data_lines) == 3
        assert data_lines[-1] == "data: [DONE]"

        first = json.loads(data_lines[0].removeprefix("data: "))
        assert first["content"] == "Bonjour"

    def test_stream_agent_unavailable(self):
        """When MCP connection fails, stream should raise 500."""
        with patch("src.app.routes.create_client", new_callable=AsyncMock) as mock_client:
            mock_client.side_effect = ConnectionError("MCP down")

            from src.app.main import app
            app.state.agent = None
            app.state.mcp_client = None
            app.state.mcp_tools = None
            app.state._mcp_lock = asyncio.Lock()

            client = TestClient(app, raise_server_exceptions=False)
            response = client.post("/chat/stream", json={
                "messages": [{"role": "user", "content": "test"}]
            })
            assert response.status_code == 500
