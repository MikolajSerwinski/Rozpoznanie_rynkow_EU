import os
from pathlib import Path
from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent.parent
RAW_DIR = BASE_DIR / os.getenv("RAW_DIR", "data/raw")
SILVER_DIR = BASE_DIR / os.getenv("SILVER_DIR", "data/silver")
GOLD_DIR = BASE_DIR / os.getenv("GOLD_DIR", "data/gold")

START_YEAR = int(os.getenv("START_YEAR", 2023))
END_YEAR = int(os.getenv("END_YEAR", 2026))
CN_CODES = os.getenv("CN_CODES", "94,9401,9403").split(",")

# Lista kodów krajów UE (importerów mebli) wg nomenklatury Eurostatu
EU_COUNTRIES = [
    "AT", "BE", "BG", "CY", "CZ", "DE", "DK", "EE", "EL", "ES", 
    "FI", "FR", "HR", "HU", "IE", "IT", "LT", "LU", "LV", "MT", 
    "NL", "PT", "RO", "SE", "SI", "SK"
]