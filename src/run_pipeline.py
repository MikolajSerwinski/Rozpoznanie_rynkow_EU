from src.ingestion.fetch_nbp import run_nbp_ingestion
from src.ingestion.fetch_macro import run_macro_ingestion
from src.ingestion.fetch_comext import run_comext_ingestion

def main():
    print("=== START POTOKU DANYCH (ETAP 1: INGESTION DO WARSTWY RAW) ===")
    run_nbp_ingestion()
    run_macro_ingestion()
    run_comext_ingestion()
    print("=== ZAKOŃCZONO POBIERANIE DANYCH SUROWYCH ===")

if __name__ == "__main__":
    main()