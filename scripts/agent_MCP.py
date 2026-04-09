import sys
from pathlib import Path
sys.path.append(str(Path(__file__).resolve().parents[1]))

import asyncio
from langchain_mcp_adapters.client import MultiServerMCPClient

from langchain.agents import create_agent
from langchain_mistralai import ChatMistralAI

from config_agent import api_key_mistral, llm_mistral

from langchain_core.messages import ToolMessage


SYSTEM_PROMPT = """
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


class MistralMCPCompat(ChatMistralAI):
    """Mistral wrapper that flattens MCP content blocks to plain strings."""

    def _fix(self, messages):
        fixed = []
        for msg in messages:
            if isinstance(msg, ToolMessage) and isinstance(msg.content, list):
                text = "\n".join(
                    b["text"] for b in msg.content
                    if isinstance(b, dict) and "text" in b
                )
                msg = msg.model_copy(update={"content": text})
            fixed.append(msg)
        return fixed

    async def agenerate(self, messages, *args, **kwargs):
        return await super().agenerate([self._fix(m) for m in messages], *args, **kwargs)

    def generate(self, messages, *args, **kwargs):
        return super().generate([self._fix(m) for m in messages], *args, **kwargs)


async def main():
    client = MultiServerMCPClient(
        {
            "OutilsImmo": {
                "transport": "http",
                "url": "http://localhost:8100/mcp",
            }
        }
    )

    tools = await client.get_tools()
    agent = create_agent(
        model=llm_mistral,
        tools=tools,
        system_prompt=SYSTEM_PROMPT,
    )

    up1 = "quelles sont les outils à ta disposition ?"
    up2 = "quelles sont les équipements de la commune de Tours ?"
    up3 = "quelles sont les 10 transactions les plus récentes pour des maisons à Tours ?"

    question = up3
    print(f"\n{'='*60}")
    print(f"[USER] {question}")
    print(f"{'='*60}")

    async for event in agent.astream_events(
        {"messages": [{"role": "user", "content": question}]},
        version="v2",
    ):
        kind = event["event"]
        data = event.get("data", {})

        if kind == "on_chat_model_start":
            print(f"\n[LLM] Appel modèle...")

        elif kind == "on_chat_model_stream":
            chunk = data.get("chunk")
            if chunk and hasattr(chunk, "content") and chunk.content:
                print(chunk.content, end="", flush=True)

        elif kind == "on_tool_start":
            tool_name = event.get("name", "?")
            inputs = data.get("input", {})
            print(f"\n\n[TOOL CALL] {tool_name}({inputs})")

        elif kind == "on_tool_end":
            tool_name = event.get("name", "?")
            output = data.get("output", "")
            print(f"[TOOL RESULT] {tool_name} → {output}")

    print(f"\n{'='*60}")


if __name__ == "__main__":
    asyncio.run(main())