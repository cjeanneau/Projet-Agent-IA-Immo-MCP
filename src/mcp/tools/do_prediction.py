
from config import MODEL


from src.inference.model import get_model, get_estimation
from typing import Any

model = get_model(MODEL)

def estimate_price(address, type_local, surface_habitable, surface_terrain, nombre_pieces) -> dict[str, Any]:
    """Lance l'inférence de prix immobilier à partir des caractéristiques du bien.

    Args:
        address (str): Adresse du bien.
        type_local (str): Type de local (ex: Maison, Appartement).
        surface_habitable (float): Surface habitable en m2.
        surface_terrain (float): Surface de terrain en m2.
        nombre_pieces (int): Nombre de pièces principales.

    Returns:
        dict[str, Any]: Résultat produit par le moteur d'estimation (prix et métadonnées).
    """
    return get_estimation(
        model,
        address,
        type_local,
        surface_habitable,
        surface_terrain,
        nombre_pieces
    )

