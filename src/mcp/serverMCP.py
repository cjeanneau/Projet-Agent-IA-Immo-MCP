from fastmcp import FastMCP
import duckdb
from config import BPE_INSEE_DB
from enum import Enum
from typing import Any
from .tools.geocoding import geocoding
from .tools.commune_info import get_commune_info
from .tools.list_transactions import get_recent_transactions
from .tools.do_prediction import estimate_price

import aiohttp
import asyncio

from tenacity import retry, stop_after_attempt, wait_exponential_jitter, retry_if_exception

class TypeBien(str, Enum):
    maison = "maison"
    appartement = "appartement"

con = duckdb.connect(BPE_INSEE_DB, read_only=True)

#Initialisation du serveur MCP avec les outils disponibles
mcp = FastMCP(
    "OutilsImmo",
    instructions="Fournis des outils pour aider à la prédiction de valeurs immobilières. Utilise ces outils pour répondre aux questions et fournir des informations pertinentes sur le marché immobilier.",
)

# ── Retry decorator pour les appels réseau ────────────────────────────────

def _is_retryable(exc):
    if isinstance(exc, aiohttp.ClientResponseError):
        return exc.status in (429, 502, 503, 504)
    return isinstance(exc, (aiohttp.ClientError, asyncio.TimeoutError, ConnectionError))

network_retry = retry(
    stop=stop_after_attempt(3),
    wait=wait_exponential_jitter(initial=2, max=10, jitter=2),
    retry=retry_if_exception(_is_retryable),
    reraise=True,
)


@mcp.tool
@network_retry
async def geocoding_tools(address: str) -> dict[str, Any]:
    print(address)
    """Obtenir les coordonnées géographiques pour une adresse donnée."""
    if not address or len(address.strip()) < 2:
        return {"error": "Adresse invalide. Veuillez fournir une adresse plus précise."}
    try:
        result = await geocoding(address)
        print(result)
        return result
    except (aiohttp.ClientError, asyncio.TimeoutError):
        raise  # laisse tenacity retry
    except Exception as e:
        return {"error": f"Geocoding échoué: {type(e).__name__}: {e}"}


@mcp.tool
async def commune_info_tools(code_insee: str) -> dict[str, Any]:
    """Obtenir les informations sur les nombres d'équipement pour un code INSEE."""
    if not code_insee or not code_insee.strip().isdigit() or len(code_insee.strip()) != 5:
        return {"error": f"Code INSEE invalide: '{code_insee}'. Attendu: 5 chiffres (ex: 37261)."}
    try:
        result = get_commune_info(con, code_insee=code_insee)
        print(result)
        if not result:
            return {"error": f"Aucune donnée trouvée pour le code INSEE {code_insee}."}
        return result
    except duckdb.Error as e:
        return {"error": f"Erreur base de données: {e}"}
    except Exception as e:
        return {"error": f"Commune info échoué: {type(e).__name__}: {e}"}

@mcp.tool
@network_retry
async def recent_transactions_tools(code_insee: str, type_bien: TypeBien, n: int = 10) -> dict[str, Any]:
    """Obtenir les informations sur les 10 transactions les plus récentes pour un code INSEE."""
    if not code_insee or not code_insee.strip().isdigit() or len(code_insee.strip()) != 5:
        return {"error": f"Code INSEE invalide: '{code_insee}'. Attendu: 5 chiffres (ex: 37261)."}
    if n < 1 or n > 50:
        n = min(max(n, 1), 50)
    try:
        result = await get_recent_transactions(code_insee=code_insee, type_bien=type_bien, top_n=n)
        if not result:
            return {"error": f"Aucune transaction trouvée pour {code_insee} ({type_bien})."}
        # get_recent_transactions retourne une liste — on l'enveloppe pour respecter dict[str, Any]
        if isinstance(result, list):
            return {"transactions": result}
        return result
    except (aiohttp.ClientError, asyncio.TimeoutError):
        raise  # laisse tenacity retry
    except Exception as e:
        return {"error": f"Transactions échoué: {type(e).__name__}: {e}"}


@mcp.tool
async def estimation_tools(
    address: str,
    type_local: str,
    surface_habitable: float,
    surface_terrain: float,
    nombre_pieces: int,
) :
    """Obtenir une estimation sur le prix de vente d'une maison ou d'un appartement située à une adresse."""
    # Validation des inputs
    if surface_habitable <= 0:
        return {"error": "La surface habitable doit être supérieure à 0."}
    if nombre_pieces < 1:
        return {"error": "Le nombre de pièces doit être au moins 1."}
    if not address or len(address.strip()) < 2:
        return {"error": "Adresse invalide."}
    try:
        result = estimate_price(address, type_local, surface_habitable, surface_terrain, nombre_pieces)
        print(result)
        return result
    except Exception as e:
        return {"error": f"Estimation échouée: {type(e).__name__}: {e}"}

'''@mcp.tool
async def geocoding_tools(address: str) -> dict[str, float]:
    """Obtenir les coordonnées géographiques pour une adresse donnée."""
    return await geocoding(address)
'''

'''@mcp.tool
async def commune_info_tools(code_insee: str) -> dict[str, Any]:
    """Obtenir les informations sur les nombres d'équipement pour un code INSEE."""
    print(code_insee)
    
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
'''


'''
@mcp.tool
async def recent_transactions_tools(code_insee: str, type_bien: TypeBien, n: int = 10) -> dict[str, float]:
    """Obtenir les transactions récentes pour un code INSEE et type de bien."""
    return await get_recent_transactions(code_insee=code_insee, type_bien=type_bien, top_n=n)

@mcp.tool
async def estimation_tools(
    address: str,
    type_local: str,
    surface_habitable: float,
    surface_terrain: float,
    nombre_pieces: int,
) -> dict[str, float]:
    """Estimer le prix d'un bien immobilier en fonction de ses caractéristiques."""
    return estimate_price(
        address=address,
        type_local=type_local,
        surface_habitable=surface_habitable,
        surface_terrain=surface_terrain,
        nombre_pieces=nombre_pieces,
    )
'''
