from fastapi import FastAPI
from .routes import router
from .monitoring.prometheus_metrics import setup_prometheus
from contextlib import asynccontextmanager
#from src.agents.tools.list_transactions import close_session

from config_agent import llm_mistral, MCP_URL
import asyncio

"""
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mcp_client = await create_client(url=MCP_URL)
    tools = await app.state.mcp_client.get_tools()
    app.state.mcp_tools = {tool.name: tool for tool in tools}
    app.state.agent = await create_agent(
        tools = tools,
        llm = llm_mistral
    )
    yield
    await close_session()
"""
@asynccontextmanager
async def lifespan(app: FastAPI):
    app.state.mcp_client = None
    app.state.mcp_tools = None
    app.state.agent = None
    app.state._mcp_lock = asyncio.Lock()
    yield

app = FastAPI(
    title="Prediction de valeurs immobilières",
    description="API de prédiction des valeurs immobilières basée sur des modèles d'apprentissage automatique.",
    version="1.0.0",
    lifespan=lifespan
)

setup_prometheus(app)

app.include_router(router)