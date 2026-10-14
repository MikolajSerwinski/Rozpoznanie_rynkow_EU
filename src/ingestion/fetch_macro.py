import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config import RAW_DIR, START_YEAR

EUROSTAT_BASE_URL = "https://ec.europa.eu/eurostat/api/dissemination/statistics/1.0/data"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_eurostat_dataset(dataset_code: str, params: list[tuple[str, str]]) -> dict:
    url = f"{EUROSTAT_BASE_URL}/{dataset_code}"
    print(f"[Eurostat Macro] Pobieranie zbioru {dataset_code}...")
    with httpx.Client(timeout=60.0) as client:
        response = client.get(url, params=params)
        response.raise_for_status()
        return response.json()

def run_macro_ingestion():
    out_dir = RAW_DIR / "eurostat_macro"
    out_dir.mkdir(parents=True, exist_ok=True)

    # 1. Ludność (tps00001)
    pop_params = [("format", "JSON"), ("lang", "EN"), ("sinceTimePeriod", str(START_YEAR))]
    pop_data = fetch_eurostat_dataset("tps00001", pop_params)
    with open(out_dir / "population_raw.json", "w", encoding="utf-8") as f:
        json.dump(pop_data, f)
    print("[Eurostat Macro] Zapisano dane o ludności (population_raw.json).")

    # 2. PKB per capita w EUR (nama_10_pc: unit=CP_EUR_HAB, na_item=B1GQ)
    gdp_params = [
        ("format", "JSON"),
        ("lang", "EN"),
        ("unit", "CP_EUR_HAB"),
        ("na_item", "B1GQ"),
        ("sinceTimePeriod", str(START_YEAR)),
    ]
    gdp_data = fetch_eurostat_dataset("nama_10_pc", gdp_params)
    with open(out_dir / "gdp_per_capita_raw.json", "w", encoding="utf-8") as f:
        json.dump(gdp_data, f)
    print("[Eurostat Macro] Zapisano dane o PKB per capita (gdp_per_capita_raw.json).")

if __name__ == "__main__":
    run_macro_ingestion()