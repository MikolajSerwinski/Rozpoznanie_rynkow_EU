# Rozpoznanie rynków eksportowych dla polskiego producenta mebli

Projekt zaliczeniowy z przedmiotu **Inżynieria danych**. Potok danych oraz aplikacja analityczna wspierająca polskiego producenta mebli w wyborze rynków eksportowych w UE na podstawie statystyk handlu międzynarodowego (Eurostat Comext), danych makroekonomicznych (Eurostat) oraz kursów walut (NBP).

## Struktura repozytorium
* `src/ingestion/` – skrypty automatycznie pobierające dane z API (Comext, Eurostat, NBP) do warstwy `data/raw/`.
* `src/transformations/` – transformacje i model danych (warstwy `silver` i `gold`).
* `tests/` – automatyczne testy jakości danych.
* `app/` – aplikacja analityczna Streamlit.
* `docs/` – pełna dokumentacja projektowa (4 perspektywy, architektura, słownik danych, ADR).

## Instrukcja uruchomienia (Stan na `tydzien-1`)

1. Sklonuj repozytorium i przejdź do katalogu projektu.
2. Skopiuj przykładowy plik konfiguracyjny:
   ```bash
   cp .env.example .env
3. Zainstaluj zależności i uruchom potok pobierania danych z pomocą uv:
    uv sync
    uv run python -m src.run_pipeline