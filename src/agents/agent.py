from langchain.agents import create_agent
from langchain_mistralai import ChatMistralAI
from langchain_google_genai import ChatGoogleGenerativeAI
from langchain_core.tools import tool
from config import BPE_INSEE_DB
from src.agents.tools.geocoding import geocoding
from src.agents.tools.commune_info import get_commune_info
from src.agents.tools.list_transactions import get_recent_transactions
from src.agents.tools.do_prediction import estimate_price
from config_agent import api_key_mistral, api_key_gemini
from typing import Union
import duckdb
import aiohttp
import asyncio
from enum import Enum
from tenacity import retry, stop_after_attempt, wait_exponential, retry_if_exception_type

class TypeBien(str, Enum):
    maison = "maison"
    appartement = "appartement"

con = duckdb.connect(BPE_INSEE_DB)

# ── Retry decorator pour les appels réseau ────────────────────────────────
network_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential(multiplier=1, min=2, max=10),
    retry=retry_if_exception_type((
        aiohttp.ClientError,
        asyncio.TimeoutError,
        ConnectionError,
    )),
    reraise=True,
)


@tool
@network_retry
async def geocoding_tools(address: str) -> dict[str, float]:
    """Obtenir les coordonnées géographiques pour une adresse donnée."""
    if not address or len(address.strip()) < 2:
        return {"error": "Adresse invalide. Veuillez fournir une adresse plus précise."}
    try:
        return await geocoding(address)
    except (aiohttp.ClientError, asyncio.TimeoutError):
        raise  # laisse tenacity retry
    except Exception as e:
        return {"error": f"Geocoding échoué: {type(e).__name__}: {e}"}


@tool
async def commune_info_tools(code_insee: str) -> dict[str, float]:
    """Obtenir les informations sur les nombres d'équipement pour un code INSEE."""
    if not code_insee or not code_insee.strip().isdigit() or len(code_insee.strip()) != 5:
        return {"error": f"Code INSEE invalide: '{code_insee}'. Attendu: 5 chiffres (ex: 37261)."}
    try:
        result = get_commune_info(con, code_insee=code_insee)
        if not result:
            return {"error": f"Aucune donnée trouvée pour le code INSEE {code_insee}."}
        return result
    except duckdb.Error as e:
        return {"error": f"Erreur base de données: {e}"}
    except Exception as e:
        return {"error": f"Commune info échoué: {type(e).__name__}: {e}"}


@tool
@network_retry
async def recent_transactions_tools(code_insee: str, type_bien: TypeBien, n: int = 10) -> dict[str, float]:
    """Obtenir les informations sur les 10 transactions les plus récentes pour un code INSEE."""
    if not code_insee or not code_insee.strip().isdigit() or len(code_insee.strip()) != 5:
        return {"error": f"Code INSEE invalide: '{code_insee}'. Attendu: 5 chiffres (ex: 37261)."}
    if n < 1 or n > 50:
        n = min(max(n, 1), 50)
    try:
        result = await get_recent_transactions(code_insee=code_insee, type_bien=type_bien, top_n=n)
        if not result:
            return {"error": f"Aucune transaction trouvée pour {code_insee} ({type_bien})."}
        return result
    except (aiohttp.ClientError, asyncio.TimeoutError):
        raise  # laisse tenacity retry
    except Exception as e:
        return {"error": f"Transactions échoué: {type(e).__name__}: {e}"}


@tool
async def estimation_tools(
    address: str,
    type_local: str,
    surface_habitable: float,
    surface_terrain: float,
    nombre_pieces: int,
) -> dict[str, float]:
    """Obtenir une estimation sur le prix de vente d'une maison ou d'un appartement située à une adresse."""
    # Validation des inputs
    if type_local not in ("maison", "appartement"):
        return {"error": f"Type '{type_local}' non supporté. Utilisez 'maison' ou 'appartement'."}
    if surface_habitable <= 0:
        return {"error": "La surface habitable doit être supérieure à 0."}
    if nombre_pieces < 1:
        return {"error": "Le nombre de pièces doit être au moins 1."}
    if not address or len(address.strip()) < 2:
        return {"error": "Adresse invalide."}
    try:
        return estimate_price(address, type_local, surface_habitable, surface_terrain, nombre_pieces)
    except Exception as e:
        return {"error": f"Estimation échouée: {type(e).__name__}: {e}"}


llm_mistral = ChatMistralAI(model="mistral-small-2503", api_key=api_key_mistral, temperature=0)
llm_gemini = ChatGoogleGenerativeAI(model="gemini-2.5-flash", api_key=api_key_gemini, temperature=0)

agent = create_agent(
    model=llm_mistral,
    tools=[geocoding_tools, commune_info_tools, recent_transactions_tools, estimation_tools],
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