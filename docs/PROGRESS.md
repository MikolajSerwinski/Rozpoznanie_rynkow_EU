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