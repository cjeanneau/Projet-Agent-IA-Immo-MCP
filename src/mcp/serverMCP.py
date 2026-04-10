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
    """Type de bien accepté par les outils de transactions."""

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
    """Résout une adresse postale en coordonnées GPS et métadonnées communales.

    Args:
        address (str): Adresse libre à géocoder (ex: "10 rue de la Paix, Paris").

    Returns:
        dict[str, Any]:
            - En succès: `adresse`, `code_insee`, `type_voie`, `longitude`, `latitude`.
            - En échec: dictionnaire avec la clé `error`.
    """
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
    """Récupère les indicateurs d'équipements d'une commune via son code INSEE.

    Args:
        code_insee (str): Code INSEE sur 5 chiffres (ex: "37261").

    Returns:
        dict[str, Any]:
            - En succès: informations de la commune (nom, volumes d'équipements par catégorie).
            - En échec: dictionnaire avec la clé `error`.
    """
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
    """Liste les transactions DVF les plus récentes d'une commune pour un type de bien.

    Args:
        code_insee (str): Code INSEE de la commune (5 chiffres).
        type_bien (TypeBien): `maison` ou `appartement`.
        n (int, optional): Nombre de résultats souhaités. Borné automatiquement entre 1 et 50.

    Returns:
        dict[str, Any]:
            - En succès: `{"transactions": [...]}` avec les mutations triées par date décroissante.
            - En échec: dictionnaire avec la clé `error`.
    """
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
    """Estime le prix de vente d'un bien à partir de son adresse et de ses caractéristiques.

    Args:
        address (str): Adresse complète du bien.
        type_local (str): Type de local attendu par le modèle (ex: "Maison", "Appartement").
        surface_habitable (float): Surface habitable en m2 (strictement positive).
        surface_terrain (float): Surface de terrain en m2 (0 possible pour un appartement).
        nombre_pieces (int): Nombre de pièces (minimum 1).

    Returns:
        dict[str, Any]:
            - En succès: estimation et variables explicatives renvoyées par le moteur de prédiction.
            - En échec: dictionnaire avec la clé `error`.
    """
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
