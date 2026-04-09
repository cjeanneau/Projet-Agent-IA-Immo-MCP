import asyncio
from langchain.agents import create_agent
from langchain_mcp_adapters.client import MultiServerMCPClient
from langchain_openai import ChatOpenAI


MCP_URL = "http://localhost:8001/mcp"
MODEL = "apple-foundationmodel"


async def run():
    client = MultiServerMCPClient(
        {
            "OutilsImmo": {
                "transport": "http",
                "url": MCP_URL,
            }
        }
    )

    tools = await client.get_tools()

    llm_local = ChatOpenAI(
        model=MODEL,
        base_url="http://localhost:11434/v1",
        api_key="unused",
        temperature=0,
    )

    agent = create_agent(
        model=llm_local,
        tools=tools,
        system_prompt=
            """
        SÉLECTION D'OUTIL — suivre strictement :
        - code INSEE, coordonnées, localiser → geocoding_tools
        - transactions, ventes, prix récents, marché → recent_transactions_tools
        - équipements, commerces, écoles, infrastructures → commune_info_tools
        - question générale sur une ville → commune_info_tools + recent_transactions_tools
        - estimation de prix → collecter infos manquantes puis estimation_tools

        WORKFLOW : toujours commencer par geocoding_tools pour obtenir le code INSEE.

        FORMAT :
        - Transactions → TOUJOURS en tableau markdown :
          | Date | Type | Surface bâtie | Surface terrain | Prix | Latitude | Longitude |
        - Équipements → liste structurée lisible
        - Estimation → format structuré ne pas mentionner le score de localisation associé a l'adresse

        ERREURS :
        - Si un outil retourne "error", expliquer et proposer une alternative.
        - Ne JAMAIS inventer de données.
        """
    )
    up1 = "quelles sont les outils à ta disposition ?"
    up2 = "quelles sont les équipements de la commune de Tours (code INSEE 37261) ?"
    up3 = "quelles sont les 10 transactions les plus récentes pour des maisons à Tours (code INSEE 37261) ?"
    response = await agent.ainvoke(
        {"messages": [{"role": "user", "content": up3}]}
    )

    print(response["messages"][-1].content)


if __name__ == "__main__":
    asyncio.run(run())