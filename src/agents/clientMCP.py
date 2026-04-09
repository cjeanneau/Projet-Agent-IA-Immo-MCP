from langchain_mcp_adapters.client import MultiServerMCPClient


async def create_client(url:str):
    # 1. Récupérer les outils MCP
    return MultiServerMCPClient(
        {
            "outils_immo": {
                "transport": "http",
                "url": url,
            }
        }
    )