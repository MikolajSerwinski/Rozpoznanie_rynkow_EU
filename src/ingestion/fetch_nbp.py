import json
from datetime import date
import httpx
from tenacity import retry, stop_after_attempt, wait_exponential
from src.config import RAW_DIR, START_YEAR, END_YEAR

@retry(stop=stop_after_attempt(3), wait=wait_exponential(multiplier=1, min=2, max=10))
def fetch_nbp_year(year: int) -> dict:
    start_date = f"{year}-01-01"
    today = date.today()
    end_date = today.isoformat() if year == today.year else f"{year}-12-31"
    
    url = f"https://api.nbp.pl/api/exchangerates/rates/a/eur/{start_date}/{end_date}/?format=json"
    print(f"[NBP] Pobieranie kursów EUR/PLN za okres {start_date} do {end_date}...")
    
    with httpx.Client(timeout=30.0) as client:
        response = client.get(url)
        response.raise_for_status()
        return response.json()

def run_nbp_ingestion():
    out_dir = RAW_DIR / "nbp"
    out_dir.mkdir(parents=True, exist_ok=True)
    
    for year in range(START_YEAR, END_YEAR + 1):
        out_file = out_dir / f"eur_pln_{year}.json"
        # Jeśli to zamknięty rok z przeszłości i plik już istnieje, nie musimy go pobierać ponownie (idempotentność)
        if out_file.exists() and year < date.today().year:
            print(f"[NBP] Plik {out_file.name} już istnieje. Pomijam.")
            continue
            
        data = fetch_nbp_year(year)
        with open(out_file, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
        print(f"[NBP] Zapisano surowy plik: {out_file}")

if __name__ == "__main__":
    run_nbp_ingestion()