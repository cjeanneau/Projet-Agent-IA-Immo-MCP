import aiohttp
from src.agents.tools.list_transactions import get_session
from typing import Any

async def geocoding(address: str) -> dict[str, Any]:
    """Obtenir les coordonnées géographiques pour une adresse donnée."""
    if not address or len(address) < 5:
        raise ValueError("Adresse invalide. Veuillez fournir une adresse complète.")

    url = "https://api-adresse.data.gouv.fr/search/"
    params = {"q": address, "limit": 1}

    try:
        session = await get_session()
        async with session.get(url, params=params) as response:
            response.raise_for_status()
            data = await response.json()
    except aiohttp.ClientError as e:
        return {"error": f"Service de géocodage indisponible: {e}"}

    if not data.get("features"):
        return {"error": f"Aucun résultat pour: {address}"}

    coords = data['features'][0]['geometry']['coordinates']
    props = data['features'][0]['properties']
    type_voie = props.get('street')
    type_voie = type_voie.split()[0] if type_voie else None

    return {
        "adresse": props['label'],
        "code_insee": props['citycode'],
        "type_voie": type_voie,
        "longitude": coords[0],
        "latitude": coords[1],
    }