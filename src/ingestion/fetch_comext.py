import json
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config import RAW_DIR, START_YEAR, END_YEAR, CN_CODES, EU_COUNTRIES

# UWAGA: Zbiory Comext (ds-*) korzystają z endpointu /api/comext/dissemination/
COMEXT_API_URL = "https://ec.europa.eu/eurostat/api/comext/dissemination/statistics/1.0/data/ds-045409"

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=2, min=4, max=20))
def fetch_comext_year(year: int) -> dict:
    params = [
        ("format", "JSON"),
        ("lang", "EN"),
        ("freq", "M"),
        ("flow", "1"),  # 1 = Import
        ("indicators", "VALUE_IN_EUROS"),
        ("indicators", "QUANTITY_IN_100KG"),
        ("partner", "PL"),
        ("partner", "WORLD"),  # Całkowity import (do wyliczenia udziału Polski)
        ("sinceTimePeriod", f"{year}-01"),
        ("untilTimePeriod", f"{year}-12"),
    ]
    
    for code in CN_CODES:
        params.append(("product", code.strip()))
    for country in EU_COUNTRIES:
        params.append(("reporter", country.strip()))

    print(f"[Comext] Pobieranie danych importowych CN ({','.join(CN_CODES)}) za rok {year}...")
    with httpx.Client(timeout=120.0) as client:
        response = client.get(COMEXT_API_URL, params=params)
        if response.status_code != 200:
            print(f"[Comext BŁĄD {response.status_code}] Odpowiedź serwera: {response.text[:500]}")
        response.raise_for_status()
        return response.json()

def run_comext_ingestion():
    out_dir = RAW_DIR / "comext"
    out_dir.mkdir(parents=True, exist_ok=True)

    for year in range(START_YEAR, END_YEAR + 1):
        out_file = out_dir / f"comext_import_{year}.json"
        if out_file.exists() and year < END_YEAR:
            print(f"[Comext] Plik {out_file.name} już istnieje (ładowanie przyrostowe). Pomijam.")
            continue

        try:
            data = fetch_comext_year(year)
            with open(out_file, "w", encoding="utf-8") as f:
                json.dump(data, f)
            print(f"[Comext] Zapisano surowy zrzut Comext: {out_file}")
        except Exception as e:
            # Jeśli dla bieżącego roku (2026) Eurostat nie opublikował jeszcze danych Comext (opóźnienie ok. 2 mies.)
            if year == END_YEAR:
                print(f"[Comext] Brak opublikowanych danych za rok {year} w bazie Comext (opóźnienie publikacji).")
            else:
                raise e

if __name__ == "__main__":
    run_comext_ingestion()