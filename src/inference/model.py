from src.utils.geo import validate_and_geocode_address
from src.utils.load_models import load_pickle
from config import MODEL
import numpy as np
from typing import Dict, Any
from pathlib import Path
import pandas as pd

class AddressNotFoundError(Exception):
    pass

def get_model(model_path : Path):
    return load_pickle(model_path)

def normalize_street_type(word: str) -> str:
    mapping = {
        "allée": "ALL", "allee": "ALL",
        "avenue": "AV",
        "boulevard": "BD",
        "chemin": "CHE",
        "impasse": "IMP",
        "place": "PL",
        "résidence": "RES", "residence": "RES",
        "route": "RTE",
        "rue": "RUE",
    }
    return mapping.get(word.lower().strip(), "NAN")

def get_estimation(
        model,
        address : str,
        type_local : str,
        surface_habitable : float,
        surface_terrain : float,
        nombre_pieces : int,
    ) -> Dict[str, Any] : 

    is_valid , geocode_data = validate_and_geocode_address(address)

    if not is_valid:
        raise AddressNotFoundError("Adresse introuvable. Veuillez vérifier l'adresse saisie.")

    validated_address = geocode_data['address']
    validated_lat = geocode_data['latitude']
    validated_lon = geocode_data['longitude']

    model_input = {
        'Type local': [type_local.title()],
        'latitude': [validated_lat],
        'longitude': [validated_lon],
        'Surface habitable': [surface_habitable],
        'Nombre pieces principales': [nombre_pieces],
        'Surface terrain': [surface_terrain],
        'Type de voie': [normalize_street_type('Boulevard')],
        'densite': [1200]
    }

    prediction = model_predict(model=model, model_input=model_input)
    confidence_margin = int(prediction * 0.05)
    context = {
        "input": {
            "type": type_local,
            "address": validated_address,
            "surface_habitable": surface_habitable,
            "nombre_pieces": nombre_pieces,
            "surface_terrain": surface_terrain
        },
        "coordinates": {
            "latitude": validated_lat,
            "longitude": validated_lon,
            "commune": geocode_data.get('citycode')
        },
        "estimation": {
            "price": prediction,
            "price_per_m2": int(prediction / surface_habitable),
            "confidence_interval": {
                "min": float(prediction - confidence_margin),
                "max": float(prediction + confidence_margin)
            },
            "confidence_level": "high" if geocode_data.get('type') == "housenumber" else "medium"
        },
        "metadata": {
            "address_score": geocode_data['score'],
            "address_type": geocode_data.get('type')
        }
    }
    return context

def model_predict(model, model_input):

    return float(np.exp(
        model.predict(
            pd.DataFrame(model_input, index=[0])
        )[0]
    ))