# Dziennik postępów projektu (PROGRESS)

## Tydzień 1 (`tydzien-1`)
* **Zrealizowane zadania:**
  * Zdefiniowano odbiorcę (polski producent mebli), problem biznesowy oraz 4 pytania analityczne w dokumentacji.
  * Skonfigurowano środowisko Python z użyciem `uv` (`pyproject.toml`, `uv.lock`) oraz warstwową strukturę katalogów (`raw`, `silver`, `gold`).
  * Rozpoznano strukturę zewnętrznych API: Eurostat Comext (`ds-045409`), Eurostat Makro (`tps00001`, `nama_10_pc`) oraz API NBP (kursy EUR/PLN).
  * Zaimplementowano automatyczne skrypty pobierające dane do warstwy `data/raw/` z obsługą ponawiania zapytań (`tenacity`), podziałem na roczne okna (obejście limitu 367 dni w API NBP) oraz mechanizmem pomijania już pobranych zamkniętych lat (podstawa pod ładowanie przyrostowe).
* **Plany na Tydzień 2:**
  * Dekodowanie formatu JSON-stat z Eurostatu i transformacja danych do warstwy `silver` (Parquet).
  * Budowa modelu analitycznego w warstwie `gold` (DuckDB) i wyliczenie metryk (dynamika importu, udział Polski, cena EUR/kg, przeliczenia walutowe).
  * Wdrożenie min. 5 automatycznych testów jakości danych w `pytest`.


## Tydzień 2 (`tydzien-2`)
* **Zrealizowane zadania:**
  * Zaimplementowano uniwersalny dekoder formatu JSON-stat 2.0 w `src/transformations/clean_silver.py`.
  * Zbudowano warstwę `silver` (pliki Parquet): ujednolicono kody krajów, zagregowano dzienne kursy NBP do średnich miesięcznych oraz przeliczono masę w Comext z jednostek `100 kg` na `kg`.
  * Zbudowano warstwę `gold` (`data/gold/analytics.duckdb` oraz pliki Parquet) z modelem gwiazdy (`dim_countries`, `fact_monthly_trade`, `mart_annual_summary`) i wyliczono kluczowe miary biznesowe (udział Polski %, cena jednostkowa EUR/kg, wartość w PLN).
  * Wdrożono 6 automatycznych testów jakości danych w `pytest` (`tests/test_data_quality.py`) weryfikujących kompletność, unikalność klucza głównego, integralność referencyjną, dozwolone wartości kodów CN, zakresy kursów NBP oraz reguły dziedzinowe.
  * Utworzono diagram architektury (`docs/02_architektura.md`) oraz pełny słownik danych (`docs/03_slownik_danych.md`).
* **Plany na Tydzień 3:**
  * Budowa interaktywnej aplikacji analitycznej w Streamlit odpowiadającej na 4 pytania producenta mebli (w tym symulator kursowy EUR/PLN).