from pathlib import Path
from dotenv import load_dotenv
import os
load_dotenv(override=True)

# Projecty root directory
ROOT = Path(__file__).parent

# Data directory
DATA_DIR = ROOT / "data"
DATA_CLEAN = DATA_DIR / "clean"
dvf_clean=DATA_CLEAN / "dvf.csv"

# Model directory
MODEL_DIR = ROOT / "model"
MODEL_CHARAC = MODEL_DIR / "characterization"

DEPLOYED_MODEL_PATH = MODEL_DIR / "model.onnx"

# DVF file
DVF = DATA_DIR / "valeursfoncieres-2025-s1.txt.zip"

# BPE file
BPE_INSEE = DATA_DIR / "BPE_INSEE"

# DuckDB
BPE_INSEE_DB = os.getenv("BPE_INSEE", str(DATA_DIR / "bpe_insee.duckdb"))

# Token database
TOKENDB = DATA_DIR / "tokendb.json"

API_CONFIG = {
    "host": "localhost",
    "port": 8222
}

# Model 
MODEL_DIR = ROOT  / 'model'
MODEL = os.getenv('MODEL', str(MODEL_DIR / 'deploy' / 'best_model3.pkl'))

