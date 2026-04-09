from langchain.agents import create_agent as _create_agent


async def create_agent(tools, llm):

    return _create_agent(
        model=llm,
        tools=tools,
        system_prompt="""
            Vous êtes un agent immobilier virtuel. Répondez toujours en français.

            OUTILS :
            1. geocoding_tools(address) → GPS + code INSEE. Paris = 1 code par arrondissement (75101-75120).
            2. commune_info_tools(code_insee) → équipements de la commune. PAS de transactions.
            3. recent_transactions_tools(code_insee, type_bien, n) → ventes récentes. PAS d'équipements.
            4. estimation_tools(address, type_local, surface_habitable, surface_terrain, nombre_pieces) → prix estimé. Maison/appartement uniquement, PAS terrain.

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


async def main():
    
    client = await create_client()
    tools = await client.get_tools()
    noms_outils = [outil.name for outil in tools]
    print("Outils MCP disponibles :", noms_outils)

    agent = await create_agent(tools=tools, llm=llm_mistral)
    

if __name__ == "__main__":
    from .clientMCP import create_client
    import asyncio
    from config_agent import llm_mistral
    asyncio.run(main())