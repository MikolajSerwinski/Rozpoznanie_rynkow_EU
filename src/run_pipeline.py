import sys
import subprocess
from src.ingestion.fetch_nbp import run_nbp_ingestion
from src.ingestion.fetch_macro import run_macro_ingestion
from src.ingestion.fetch_comext import run_comext_ingestion
from src.transformations.clean_silver import run_silver_transformations
from src.transformations.build_gold import run_gold_transformations

def main():
    print("=== START POTOKU DANYCH (ETAP 1: INGESTION DO WARSTWY RAW) ===")
    run_nbp_ingestion()
    run_macro_ingestion()
    run_comext_ingestion()
    print("=== ZAKOŃCZONO POBIERANIE DANYCH SUROWYCH ===")
    
    print("\n=== ETAP 2: TRANSFORMACJE (WARSTWA SILVER - PARQUET) ===")
    run_silver_transformations()

    print("\n=== ETAP 3: MODEL ANALITYCZNY (WARSTWA GOLD - DUCKDB & PARQUET) ===")
    run_gold_transformations()
    
    print("\n=== ETAP 4: AUTOMATYCZNE TESTY JAKOŚCI DANYCH (PYTEST) ===")
    result = subprocess.run([sys.executable, "-m", "pytest", "-v", "tests/test_data_quality.py"])
    if result.returncode != 0:
        print("\n[BŁĄD KRYTYCZNY] Testy jakości danych nie powiodły się! Sprawdź logi powyżej.")
        sys.exit(result.returncode)
    print("\n=== SUKCES: POTOK DANYCH ZAKOŃCZONY, WSZYSTKIE TESTY JAKOŚCI ZALICZONE! ===")

if __name__ == "__main__":
    main()